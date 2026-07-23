#!/usr/bin/env python3
"""Sync Oura Ring API v2 into PostgreSQL.

Incremental runs re-pull recentDays. Set BACKFILL=1 and START_DATE for history.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

log = logging.getLogger("oura")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

API = "https://api.ouraring.com/v2/usercollection"
TOKEN_PATH = Path(os.environ.get("OURA_TOKEN_PATH", "/token/oauth_token.json"))
RECENT_DAYS = int(os.environ.get("OURA_RECENT_DAYS", "14"))
HR_CHUNK_DAYS = int(os.environ.get("OURA_HR_CHUNK_DAYS", "7"))
PAGE_SLEEP = float(os.environ.get("OURA_PAGE_SLEEP", "0.25"))
BACKFILL = os.environ.get("BACKFILL", "0") == "1"
START_DATE = os.environ.get("START_DATE", "2015-01-01")
STAGE = {"1": "deep", "2": "light", "3": "rem", "4": "awake"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS personal_info (
  id int PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  email text, age int, weight double precision, height double precision,
  biological_sex text, raw jsonb NOT NULL DEFAULT '{}',
  updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS daily_activity (
  id text PRIMARY KEY, day date NOT NULL UNIQUE, score double precision,
  steps double precision, active_calories double precision, total_calories double precision,
  raw jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS daily_readiness (
  id text PRIMARY KEY, day date NOT NULL UNIQUE, score double precision,
  temperature_deviation double precision, temperature_trend_deviation double precision,
  contributors jsonb NOT NULL DEFAULT '{}', raw jsonb NOT NULL DEFAULT '{}',
  updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS daily_sleep (
  id text PRIMARY KEY, day date NOT NULL UNIQUE, score double precision,
  contributors jsonb NOT NULL DEFAULT '{}', raw jsonb NOT NULL DEFAULT '{}',
  updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS daily_spo2 (
  id text PRIMARY KEY, day date NOT NULL UNIQUE,
  spo2_percentage_average double precision, breathing_disturbance_index double precision,
  raw jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS daily_stress (
  id text PRIMARY KEY, day date NOT NULL UNIQUE,
  stress_high double precision, recovery_high double precision, day_summary text,
  raw jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sleep_period (
  id text PRIMARY KEY, day date, bedtime_start timestamptz, bedtime_end timestamptz,
  average_breath double precision, average_heart_rate double precision, average_hrv double precision,
  awake_time double precision, deep_sleep_duration double precision,
  light_sleep_duration double precision, rem_sleep_duration double precision,
  total_sleep_duration double precision, efficiency double precision, latency double precision,
  lowest_heart_rate double precision, restless_periods double precision, type text,
  raw jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS sleep_period_day_idx ON sleep_period (day);
CREATE INDEX IF NOT EXISTS sleep_period_bedtime_idx ON sleep_period (bedtime_start);
CREATE TABLE IF NOT EXISTS sleep_stage (
  sleep_id text NOT NULL REFERENCES sleep_period (id) ON DELETE CASCADE,
  start_ts timestamptz NOT NULL, end_ts timestamptz NOT NULL, stage text NOT NULL,
  PRIMARY KEY (sleep_id, start_ts));
CREATE INDEX IF NOT EXISTS sleep_stage_range_idx ON sleep_stage (start_ts, end_ts);
CREATE TABLE IF NOT EXISTS heartrate (
  ts timestamptz PRIMARY KEY, bpm int NOT NULL, source text);
CREATE TABLE IF NOT EXISTS sync_state (
  resource text PRIMARY KEY, high_watermark timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now());
GRANT SELECT ON ALL TABLES IN SCHEMA public TO oura_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO oura_ro;
"""


def db():
    return psycopg.connect(
        host=os.environ.get("PGHOST", "postgres-rw.postgres.svc.cluster.local"),
        port=int(os.environ.get("PGPORT", "5432")),
        dbname=os.environ.get("PGDATABASE", "oura"),
        user=os.environ.get("PGUSER", "oura"),
        password=os.environ["PGPASSWORD"],
    )


def load_token() -> dict:
    # Prefer personal access token (Airbyte-style); else OAuth JSON on PVC.
    if pat := os.environ.get("OURA_PAT"):
        return {"access_token": pat, "pat": True}
    return json.loads(TOKEN_PATH.read_text())


def save_token(tok: dict) -> None:
    if tok.get("pat"):
        return
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(tok, indent=2))


def refresh_token(tok: dict) -> dict:
    if tok.get("pat"):
        raise RuntimeError("OURA_PAT rejected (401); rotate the personal access token")
    body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": tok["refresh_token"],
            "client_id": os.environ["OURA_CLIENT_ID"],
            "client_secret": os.environ["OURA_CLIENT_SECRET"],
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.ouraring.com/oauth/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    tok = {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", tok.get("refresh_token")),
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(seconds=int(data["expires_in"]))
        ).isoformat(),
    }
    save_token(tok)
    log.info("refreshed oauth token")
    return tok


def api_get(tok: dict, path: str, params: dict) -> tuple[dict | None, dict, int]:
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{API}/{path}?{qs}" if qs else f"{API}/{path}"

    def do(access: str):
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access}"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode()), 200
        except urllib.error.HTTPError as e:
            return {"error": e.read().decode()[:500]}, e.code

    data, code = do(tok["access_token"])
    if code == 401:
        tok = refresh_token(tok)
        data, code = do(tok["access_token"])
    if code == 429:
        time.sleep(5)
        data, code = do(tok["access_token"])
    return (None, tok, code) if code >= 400 else (data, tok, code)


def fetch_all(tok: dict, path: str, params: dict) -> tuple[list, dict, int]:
    items, next_token, code = [], None, 200
    while True:
        p = dict(params)
        if next_token:
            p["next_token"] = next_token
        data, tok, code = api_get(tok, path, p)
        if data is None:
            return items, tok, code
        items.extend(data.get("data") or [])
        next_token = data.get("next_token")
        if not next_token:
            return items, tok, code
        time.sleep(PAGE_SLEEP)


def parse_ts(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def watermark(conn, resource: str) -> datetime | None:
    with conn.cursor() as cur:
        cur.execute("SELECT high_watermark FROM sync_state WHERE resource = %s", (resource,))
        row = cur.fetchone()
        return row[0] if row else None


def set_watermark(conn, resource: str, ts: datetime) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO sync_state (resource, high_watermark, updated_at) VALUES (%s,%s,now())
               ON CONFLICT (resource) DO UPDATE
               SET high_watermark=EXCLUDED.high_watermark, updated_at=now()""",
            (resource, ts),
        )
    conn.commit()


def hist_start(conn, resource: str) -> date:
    if BACKFILL:
        return date.fromisoformat(START_DATE)
    wm = watermark(conn, resource)
    return (wm.date() - timedelta(days=1)) if wm else date.fromisoformat(START_DATE)


def range_start(conn, resource: str) -> date:
    return min(hist_start(conn, resource), date.today() - timedelta(days=RECENT_DAYS))


def upsert_personal(conn, tok: dict) -> dict:
    data, tok, code = api_get(tok, "personal_info", {})
    if not data or code >= 400:
        log.warning("personal_info skipped code=%s", code)
        return tok
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO personal_info (id, email, age, weight, height, biological_sex, raw, updated_at)
               VALUES (1,%s,%s,%s,%s,%s,%s,now())
               ON CONFLICT (id) DO UPDATE SET
                 email=EXCLUDED.email, age=EXCLUDED.age, weight=EXCLUDED.weight,
                 height=EXCLUDED.height, biological_sex=EXCLUDED.biological_sex,
                 raw=EXCLUDED.raw, updated_at=now()""",
            (
                data.get("email"),
                data.get("age"),
                data.get("weight"),
                data.get("height"),
                data.get("biological_sex"),
                Jsonb(data),
            ),
        )
    conn.commit()
    return tok


def upsert_daily(conn, table: str, rows: list, cols: list[str], values) -> int:
    col_sql = ", ".join(["id", "day", *cols, "raw", "updated_at"])
    placeholders = ", ".join(["%s"] * (3 + len(cols))) + ", now()"
    updates = ", ".join([f"{c}=EXCLUDED.{c}" for c in ("id", *cols, "raw")]) + ", updated_at=now()"
    sql = f"""INSERT INTO {table} ({col_sql}) VALUES ({placeholders})
              ON CONFLICT (day) DO UPDATE SET {updates}"""
    with conn.cursor() as cur:
        for r in rows:
            cur.execute(sql, values(r))
    conn.commit()
    return len(rows)


def sync_daily(conn, tok, name: str, cols: list[str], values) -> dict:
    start, today = range_start(conn, name), date.today()
    rows, tok, code = fetch_all(tok, name, {"start_date": start.isoformat(), "end_date": today.isoformat()})
    if code in (401, 403):
        log.warning("%s unavailable code=%s", name, code)
        return tok
    if code >= 400:
        log.error("%s failed code=%s", name, code)
        return tok
    n = upsert_daily(conn, name, rows, cols, values)
    set_watermark(conn, name, datetime.now(timezone.utc))
    log.info("%s upserted=%s range=%s..%s", name, n, start, today)
    return tok


def expand_stages(sleep_id: str, start: datetime | None, phase: str | None) -> list[tuple]:
    if not start or not phase:
        return []
    out, i = [], 0
    while i < len(phase):
        j = i + 1
        while j < len(phase) and phase[j] == phase[i]:
            j += 1
        out.append(
            (
                sleep_id,
                start + timedelta(minutes=5 * i),
                start + timedelta(minutes=5 * j),
                STAGE.get(phase[i], phase[i]),
            )
        )
        i = j
    return out


def sync_sleep(conn, tok) -> dict:
    start, today = range_start(conn, "sleep"), date.today()
    rows, tok, code = fetch_all(tok, "sleep", {"start_date": start.isoformat(), "end_date": today.isoformat()})
    if code >= 400:
        log.warning("sleep skipped code=%s", code)
        return tok
    with conn.cursor() as cur:
        for r in rows:
            sid, bs, be = r["id"], parse_ts(r.get("bedtime_start")), parse_ts(r.get("bedtime_end"))
            cur.execute(
                """INSERT INTO sleep_period (
                     id, day, bedtime_start, bedtime_end, average_breath, average_heart_rate, average_hrv,
                     awake_time, deep_sleep_duration, light_sleep_duration, rem_sleep_duration,
                     total_sleep_duration, efficiency, latency, lowest_heart_rate, restless_periods,
                     type, raw, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                   ON CONFLICT (id) DO UPDATE SET
                     day=EXCLUDED.day, bedtime_start=EXCLUDED.bedtime_start, bedtime_end=EXCLUDED.bedtime_end,
                     average_breath=EXCLUDED.average_breath, average_heart_rate=EXCLUDED.average_heart_rate,
                     average_hrv=EXCLUDED.average_hrv, awake_time=EXCLUDED.awake_time,
                     deep_sleep_duration=EXCLUDED.deep_sleep_duration,
                     light_sleep_duration=EXCLUDED.light_sleep_duration,
                     rem_sleep_duration=EXCLUDED.rem_sleep_duration,
                     total_sleep_duration=EXCLUDED.total_sleep_duration,
                     efficiency=EXCLUDED.efficiency, latency=EXCLUDED.latency,
                     lowest_heart_rate=EXCLUDED.lowest_heart_rate, restless_periods=EXCLUDED.restless_periods,
                     type=EXCLUDED.type, raw=EXCLUDED.raw, updated_at=now()""",
                (
                    sid,
                    r.get("day"),
                    bs,
                    be,
                    r.get("average_breath"),
                    r.get("average_heart_rate"),
                    r.get("average_hrv"),
                    r.get("awake_time"),
                    r.get("deep_sleep_duration"),
                    r.get("light_sleep_duration"),
                    r.get("rem_sleep_duration"),
                    r.get("total_sleep_duration"),
                    r.get("efficiency"),
                    r.get("latency"),
                    r.get("lowest_heart_rate"),
                    r.get("restless_periods"),
                    r.get("type"),
                    Jsonb(r),
                ),
            )
            cur.execute("DELETE FROM sleep_stage WHERE sleep_id = %s", (sid,))
            for st in expand_stages(sid, bs, r.get("sleep_phase_5_min")):
                cur.execute(
                    "INSERT INTO sleep_stage (sleep_id, start_ts, end_ts, stage) VALUES (%s,%s,%s,%s)",
                    st,
                )
    conn.commit()
    set_watermark(conn, "sleep", datetime.now(timezone.utc))
    log.info("sleep upserted=%s range=%s..%s", len(rows), start, today)
    return tok


def sync_heartrate(conn, tok) -> dict:
    end = datetime.now(timezone.utc)
    if BACKFILL:
        cur = datetime.fromisoformat(START_DATE).replace(tzinfo=timezone.utc)
    else:
        wm = watermark(conn, "heartrate")
        recent = end - timedelta(days=RECENT_DAYS)
        cur = min(wm - timedelta(days=1), recent) if wm else datetime.fromisoformat(START_DATE).replace(
            tzinfo=timezone.utc
        )
    total = 0
    while cur < end:
        chunk_end = min(cur + timedelta(days=HR_CHUNK_DAYS), end)
        rows, tok, code = fetch_all(
            tok,
            "heartrate",
            {"start_datetime": cur.isoformat(), "end_datetime": chunk_end.isoformat()},
        )
        if code in (401, 403):
            log.warning("heartrate unavailable code=%s", code)
            return tok
        if code < 400:
            with conn.cursor() as c:
                for r in rows:
                    ts = parse_ts(r.get("timestamp"))
                    if not ts or r.get("bpm") is None:
                        continue
                    c.execute(
                        """INSERT INTO heartrate (ts, bpm, source) VALUES (%s,%s,%s)
                           ON CONFLICT (ts) DO UPDATE SET bpm=EXCLUDED.bpm, source=EXCLUDED.source""",
                        (ts, int(r["bpm"]), r.get("source")),
                    )
                    total += 1
            conn.commit()
            log.info("heartrate chunk %s..%s rows=%s", cur.date(), chunk_end.date(), len(rows))
        else:
            log.error("heartrate chunk failed %s..%s code=%s", cur, chunk_end, code)
        cur = chunk_end
        time.sleep(PAGE_SLEEP)
    set_watermark(conn, "heartrate", end)
    log.info("heartrate total upserted=%s", total)
    return tok


def main() -> None:
    log.info("start BACKFILL=%s START_DATE=%s", BACKFILL, START_DATE)
    tok = load_token()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
        tok = upsert_personal(conn, tok)
        tok = sync_daily(
            conn,
            tok,
            "daily_activity",
            ["score", "steps", "active_calories", "total_calories"],
            lambda r: (
                r["id"],
                r.get("day"),
                r.get("score"),
                r.get("steps"),
                r.get("active_calories"),
                r.get("total_calories"),
                Jsonb(r),
            ),
        )
        tok = sync_daily(
            conn,
            tok,
            "daily_readiness",
            ["score", "temperature_deviation", "temperature_trend_deviation", "contributors"],
            lambda r: (
                r["id"],
                r.get("day"),
                r.get("score"),
                r.get("temperature_deviation"),
                r.get("temperature_trend_deviation"),
                Jsonb(r.get("contributors") or {}),
                Jsonb(r),
            ),
        )
        tok = sync_daily(
            conn,
            tok,
            "daily_sleep",
            ["score", "contributors"],
            lambda r: (r["id"], r.get("day"), r.get("score"), Jsonb(r.get("contributors") or {}), Jsonb(r)),
        )
        tok = sync_daily(
            conn,
            tok,
            "daily_spo2",
            ["spo2_percentage_average", "breathing_disturbance_index"],
            lambda r: (
                r["id"],
                r.get("day"),
                (r.get("spo2_percentage") or {}).get("average"),
                r.get("breathing_disturbance_index"),
                Jsonb(r),
            ),
        )
        tok = sync_daily(
            conn,
            tok,
            "daily_stress",
            ["stress_high", "recovery_high", "day_summary"],
            lambda r: (
                r["id"],
                r.get("day"),
                r.get("stress_high"),
                r.get("recovery_high"),
                r.get("day_summary"),
                Jsonb(r),
            ),
        )
        tok = sync_sleep(conn, tok)
        sync_heartrate(conn, tok)
    log.info("done")


if __name__ == "__main__":
    main()
