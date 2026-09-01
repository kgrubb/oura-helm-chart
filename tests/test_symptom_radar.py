"""Tests for Symptom Radar v4."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from oura_collector.symptom_radar import ALGO, Night, score_night

FIXTURES = Path(__file__).parent / "fixtures" / "symptom_radar_ground_truth.json"


def _healthy_night(day: date, rr: float = 14.75) -> Night:
    return Night(
        day=day,
        body_temperature=92.0,
        hrv_balance=88.0,
        resting_heart_rate=88.0,
        recovery_index=85.0,
        previous_day_activity=88.0,
        temp=0.0,
        rr=rr,
    )


def _build_history(scored_day: date, rr_baseline: float = 14.75) -> list[Night]:
    hist: list[Night] = []
    end = scored_day - timedelta(days=4)
    for i in range(35):
        d = end - timedelta(days=34 - i)
        hist.append(_healthy_night(d, rr=rr_baseline))
    return hist


def _night_from_dict(data: dict) -> Night:
    return Night(
        day=date.fromisoformat(data["day"]),
        body_temperature=data.get("body_temperature"),
        hrv_balance=data.get("hrv_balance"),
        resting_heart_rate=data.get("resting_heart_rate"),
        recovery_index=data.get("recovery_index"),
        previous_day_activity=data.get("previous_day_activity"),
        temp=data.get("temp"),
        rr=data.get("rr"),
    )


def _load_cases() -> list[dict]:
    return json.loads(FIXTURES.read_text())["cases"]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["label"])
def test_scoring_cases(case: dict) -> None:
    night = _night_from_dict(case["night"])
    n_hist = case.get("history_nights", 35)
    if n_hist < 10:
        history = [_healthy_night(night.day - timedelta(days=i + 1)) for i in range(n_hist)]
    else:
        rr_base = case.get("rr_baseline", case["night"].get("rr", 14.75))
        history = _build_history(night.day, rr_baseline=rr_base)
    result = score_night(night, history)
    assert result["level"] == case["expected"], (
        f"{case['label']}: expected {case['expected']}, got {result['level']} "
        f"(score={result['score']}, signals={result['contributors']})"
    )


def test_insufficient_data_empty_history() -> None:
    day = date(2026, 3, 20)
    night = Night(day=day, body_temperature=90, temp=0.6, rr=15)
    result = score_night(night, [])
    assert result["level"] == "insufficient_data"
    assert result["algorithm_version"] == ALGO


def test_none_healthy() -> None:
    day = date(2026, 3, 20)
    hist = _build_history(day)
    result = score_night(_healthy_night(day), hist)
    assert result["level"] == "none"
    assert result["summary_text"] == "no signs"
    assert result["algorithm_version"] == ALGO


def test_persistence_escalates() -> None:
    day = date(2026, 4, 13)
    hist = _build_history(day)
    night = Night(
        day=day,
        body_temperature=100,
        hrv_balance=82,
        resting_heart_rate=71,
        recovery_index=40,
        previous_day_activity=77,
        temp=-0.13,
        rr=14.375,
    )
    assert score_night(night, hist)["level"] == "none"
    assert score_night(night, hist, prev_level="minor")["level"] == "minor"
