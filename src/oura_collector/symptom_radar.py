"""Symptom Radar v4: readiness-contributor scoring with raw temp and RR supplements.

Approximates Oura Symptom Radar from API data. Not a replica of the on-device model.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

ALGO = "v4"
BASELINE_NIGHTS = 28
GAP_DAYS = 3
MIN_NIGHTS_14D = 7

_CONTRIBUTOR_SIGNALS = (
    "body_temperature",
    "hrv_balance",
    "resting_heart_rate",
    "recovery_index",
    "previous_day_activity",
)

_CONTRIBUTOR_THRESHOLDS: dict[str, tuple[tuple[int, int], ...]] = {
    "body_temperature": ((85, 0), (70, 1), (0, 2)),
    "hrv_balance": ((85, 0), (70, 1), (0, 2)),
    "resting_heart_rate": ((75, 0), (55, 1), (0, 2)),
    "recovery_index": ((65, 0), (35, 1), (0, 2)),
    "previous_day_activity": ((85, 0), (75, 1), (0, 2)),
}

_LEVEL_LABEL = {
    "none": "no signs",
    "minor": "Minor Signs",
    "major": "Major signs",
    "insufficient_data": "n/a",
}


@dataclass(frozen=True)
class Night:
    day: date
    body_temperature: float | None = None
    hrv_balance: float | None = None
    resting_heart_rate: float | None = None
    recovery_index: float | None = None
    previous_day_activity: float | None = None
    temp: float | None = None
    rr: float | None = None


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


def _contributor_points(signal: str, value: float | None) -> int:
    if value is None:
        return 0
    for floor, points in _CONTRIBUTOR_THRESHOLDS.get(signal, ((85, 0), (70, 1), (0, 2))):
        if value >= floor:
            return points
    return 0


def _level(score: int, n_signals: int, ok: bool, prev_level: str | None) -> str:
    if not ok:
        return "insufficient_data"
    if score >= 8 and n_signals >= 3:
        return "major"
    if score >= 5 and n_signals >= 2:
        return "minor"
    if score >= 3 and n_signals >= 2 and prev_level in ("minor", "major"):
        return "minor"
    return "none"


def score_night(
    night: Night,
    history: list[Night],
    prev_level: str | None = None,
) -> dict[str, Any]:
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

    def add(signal: str, value: float | None, points: int, **extra: Any) -> None:
        nonlocal score
        if points <= 0 or value is None:
            return
        entry: dict[str, Any] = {"signal": signal, "value": value, "points": points}
        entry.update(extra)
        contrib.append(entry)
        score += points

    for signal in _CONTRIBUTOR_SIGNALS:
        value = getattr(night, signal)
        add(signal, value, _contributor_points(signal, value))

    if (
        night.body_temperature is not None
        and night.hrv_balance is not None
        and night.body_temperature < 80
        and night.hrv_balance < 80
    ):
        add("pattern", 1.0, 1)

    if night.temp is not None and night.body_temperature is not None:
        tp = 0
        if night.temp >= 0.45 and night.body_temperature < 80:
            tp = 2
        elif night.temp >= 0.35 and night.body_temperature < 85:
            tp = 1
        add("temp", night.temp, tp)

    rr_b = series("rr")
    rrz = _z(night.rr, rr_b)
    rrp = 0
    if night.rr is not None:
        if rrz is not None and rrz >= 2.5:
            rrp = 2
        elif rrz is not None and rrz >= 2.0:
            rrp = 1
        add(
            "rr",
            night.rr,
            rrp,
            baseline=_median(rr_b) if rr_b else None,
            z=round(rrz, 3) if rrz is not None else None,
        )

    fired = [c for c in contrib if c["points"] > 0]
    level = _level(score, len(fired), ok, prev_level)

    return {
        "day": night.day,
        "level": level,
        "score": score if ok else 0,
        "n_baseline_nights": n_base,
        "n_signals": len(fired),
        "contributors": fired,
        "summary_text": _LEVEL_LABEL[level],
        "algorithm_version": ALGO,
    }
