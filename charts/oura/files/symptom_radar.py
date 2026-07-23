"""Symptom Radar proxy: TemPredict/Ultrahuman-style multimodal baseline scoring.

Local only. No third-party inference. algorithm_version=proxy-v1.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

ALGO = "proxy-v1"
BASELINE_NIGHTS = 28
GAP_DAYS = 3
MIN_NIGHTS_14D = 7


@dataclass(frozen=True)
class Night:
    day: date
    temp: float | None = None
    rhr: float | None = None
    hrv: float | None = None
    rr: float | None = None
    inactive: float | None = None  # previous calendar day sedentary_time
    sleep_s: float | None = None
    rem_s: float | None = None


def _median(xs: list[float]) -> float:
    return float(statistics.median(xs))


def _sigma(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    med = _median(xs)
    mad = _median([abs(x - med) for x in xs])
    if mad > 0:
        return 1.4826 * mad
    return float(statistics.stdev(xs))


def _z(value: float | None, base: list[float]) -> float | None:
    if value is None or len(base) < 2:
        return None
    sig = _sigma(base)
    if sig <= 0:
        return 0.0
    return (value - _median(base)) / sig


def _pts_high(z: float | None, value: float | None, abs1: float | None, abs2: float | None,
              z1: float = 1.0, z2: float = 1.5) -> int:
    """Points for signals where higher = strain."""
    p = 0
    if z is not None:
        if z >= z2:
            p = 2
        elif z >= z1:
            p = 1
    if value is not None and abs2 is not None and value >= abs2:
        p = max(p, 2)
    elif value is not None and abs1 is not None and value >= abs1:
        p = max(p, 1)
    return p


def _pts_low_z(z: float | None, value: float | None, baseline: float | None,
               pct1: float, pct2: float, z1: float = -1.0, z2: float = -1.5) -> int:
    """Points for signals where lower = strain (HRV)."""
    p = 0
    if z is not None:
        if z <= z2:
            p = 2
        elif z <= z1:
            p = 1
    if value is not None and baseline and baseline > 0:
        if value <= baseline * pct2:
            p = max(p, 2)
        elif value <= baseline * pct1:
            p = max(p, 1)
    return p


def _level(score: int, ok: bool) -> str:
    if not ok:
        return "insufficient_data"
    if score >= 3:
        return "major"
    if score == 2:
        return "minor"
    return "none"


def _fmt(c: dict) -> str:
    s, v, b, z, p = c["signal"], c.get("value"), c.get("baseline"), c.get("z"), c["points"]
    bits = [s]
    if v is not None:
        bits.append(f"{v:.2g}" if isinstance(v, float) else str(v))
    if z is not None:
        bits.append(f"z={z:.1f}")
    bits.append(f"+{p}")
    return " ".join(bits)


def score_night(night: Night, history: list[Night]) -> dict[str, Any]:
    """Score one night against prior history (must not include night itself)."""
    gate_start = night.day - timedelta(days=13)
    recent = [h for h in history if gate_start <= h.day < night.day]
    ok = len(recent) >= MIN_NIGHTS_14D

    base_end = night.day - timedelta(days=GAP_DAYS)
    base_start = base_end - timedelta(days=BASELINE_NIGHTS - 1)
    baseline_nights = [h for h in history if base_start <= h.day <= base_end]
    n_base = len(baseline_nights)

    def series(attr: str) -> list[float]:
        return [getattr(h, attr) for h in baseline_nights if getattr(h, attr) is not None]

    contrib: list[dict] = []
    score = 0

    def add(signal: str, value: float | None, base_vals: list[float], points: int) -> None:
        nonlocal score
        if points <= 0 or value is None:
            return
        z = _z(value, base_vals) if len(base_vals) >= 2 else None
        contrib.append({
            "signal": signal,
            "value": value,
            "baseline": _median(base_vals) if base_vals else None,
            "z": round(z, 3) if z is not None else None,
            "points": points,
        })
        score += points

    temp_b, rhr_b, hrv_b, rr_b, ina_b, sleep_b, rem_b = (
        series("temp"), series("rhr"), series("hrv"), series("rr"),
        series("inactive"), series("sleep_s"), series("rem_s"),
    )

    # Temperature: absolute °C on Oura deviation + z of deviation series
    tz = _z(night.temp, temp_b)
    tp = 0
    if night.temp is not None:
        if night.temp >= 0.5 or (tz is not None and tz >= 2.0):
            tp = 2
        elif night.temp >= 0.3 or (tz is not None and tz >= 1.0):
            tp = 1
    add("temp", night.temp, temp_b, tp)

    # RHR ↑
    rz = _z(night.rhr, rhr_b)
    rp = 0
    if night.rhr is not None:
        med = _median(rhr_b) if rhr_b else None
        if (rz is not None and rz >= 1.5) or (med and night.rhr >= med + 5):
            rp = 2
        elif (rz is not None and rz >= 1.0) or (med and med > 0 and night.rhr >= med * 1.05):
            rp = 1
    add("rhr", night.rhr, rhr_b, rp)

    # HRV ↓
    hz = _z(night.hrv, hrv_b)
    hp = _pts_low_z(hz, night.hrv, _median(hrv_b) if hrv_b else None, 0.90, 0.80)
    add("hrv", night.hrv, hrv_b, hp)

    # RR ↑
    rrz = _z(night.rr, rr_b)
    rrp = 0
    if night.rr is not None:
        med = _median(rr_b) if rr_b else None
        if (rrz is not None and rrz >= 1.5) or (med is not None and night.rr >= med + 1.5):
            rrp = 2
        elif (rrz is not None and rrz >= 1.0) or (med is not None and night.rr >= med + 1.0):
            rrp = 1
    add("rr", night.rr, rr_b, rrp)

    # Inactive ↑
    iz = _z(night.inactive, ina_b)
    ip = _pts_high(iz, night.inactive, None, None, z1=1.0, z2=1.5)
    add("inactive", night.inactive, ina_b, ip)

    # Sleep duration support (1 pt)
    if night.sleep_s is not None and sleep_b:
        med = _median(sleep_b)
        if night.sleep_s <= med - 3600:
            add("sleep", night.sleep_s, sleep_b, 1)

    # REM support (1 pt)
    if night.rem_s is not None and rem_b:
        med = _median(rem_b)
        if med > 0 and night.rem_s <= med * 0.80:
            add("rem", night.rem_s, rem_b, 1)

    level = _level(score, ok)
    fired = [c for c in contrib if c["points"] > 0]
    if level == "insufficient_data":
        summary = "insufficient_data: need ≥7 nights in 14d"
    elif not fired:
        summary = "none"
    else:
        summary = f"{level}: " + ", ".join(_fmt(c) for c in fired)

    return {
        "day": night.day,
        "level": level,
        "score": score if ok else 0,
        "n_baseline_nights": n_base,
        "n_signals": len(fired),
        "contributors": fired,
        "summary_text": summary,
        "algorithm_version": ALGO,
    }
