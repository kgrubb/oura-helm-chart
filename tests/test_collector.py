"""Unit tests for collector helpers that do not require PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from oura_collector import collector


def test_load_schema_contains_core_tables() -> None:
    schema = collector.load_schema()
    assert "CREATE TABLE IF NOT EXISTS personal_info" in schema
    assert "CREATE TABLE IF NOT EXISTS symptom_radar_daily" in schema
    assert Path(collector.__file__).resolve().with_name("schema.sql") == collector.SCHEMA_PATH


def test_parse_ts_handles_zulu_and_none() -> None:
    assert collector.parse_ts(None) is None
    parsed = collector.parse_ts("2026-07-20T12:34:56Z")
    assert parsed == datetime(2026, 7, 20, 12, 34, 56, tzinfo=UTC)


def test_jdump_passthrough_and_json() -> None:
    assert collector.jdump(None) is None
    assert collector.jdump("already") == "already"
    assert collector.jdump({"a": 1}) == '{"a": 1}'


def test_expand_stages_runs_of_codes() -> None:
    start = datetime(2026, 7, 20, 23, 0, tzinfo=UTC)
    stages = collector.expand_stages("sleep-1", start, "11223344")
    assert stages == [
        ("sleep-1", start, start.replace(minute=10), "deep"),
        ("sleep-1", start.replace(minute=10), start.replace(minute=20), "light"),
        ("sleep-1", start.replace(minute=20), start.replace(minute=30), "rem"),
        ("sleep-1", start.replace(minute=30), start.replace(minute=40), "awake"),
    ]


def test_expand_stages_empty_inputs() -> None:
    assert collector.expand_stages("sleep-1", None, "12") == []
    assert collector.expand_stages("sleep-1", datetime.now(UTC), None) == []


def test_pick_sleep_prefers_long_sleep() -> None:
    rows = [
        ("a", "sleep", 50, 40, 14, 1000),
        ("b", "long_sleep", 52, 45, 14, 2000),
        ("c", "long_sleep", 51, 44, 14, 1500),
    ]
    assert collector._pick_sleep(rows) == ("b", "long_sleep", 52, 45, 14, 2000)


def test_pick_sleep_falls_back_when_no_long() -> None:
    rows = [
        ("a", "sleep", 50, 40, 14, 1000),
        ("b", "sleep", 52, 45, 14, 2500),
    ]
    assert collector._pick_sleep(rows) == ("b", "sleep", 52, 45, 14, 2500)
    assert collector._pick_sleep([]) is None
