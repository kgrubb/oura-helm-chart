"""Symptom Radar: overnight biometric baseline scoring (v3).

Calibrated against labeled nights. Uses temp, temp trend, RHR, HRV, RR,
and previous-day sedentary time.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

ALGO = "v3"
BASELINE_NIGHTS = 28
GAP_DAYS = 3
MIN_NIGHTS_14D = 7

_LEVEL_LABEL = {
    "none": "no signs",
    "minor": "Minor Signs",
    "major": "Major signs",
    "insufficient_data": "—",
}


@dataclass(frozen=True)
class Night:
    day: date
    temp: float | None = None
    trend: float | None = None  # temperature_trend_deviation
    rhr: float | None = None
    hrv: float | None = None
    rr: float | None = None
    inactive: float | None = None  # previous calendar day sedentary_time


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


def _level(score: int, n_signals: int, ok: bool) -> str:
    if not ok:
        return "insufficient_data"
    if score >= 4 and n_signals >= 1:
        return "major"
    if score >= 2:
        return "minor"
    return "none"


def score_night(night: Night, history: list[Night]) -> dict[str, Any]:
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

    temp_b, trend_b, rhr_b, hrv_b, rr_b, ina_b = (
        series("temp"), series("trend"), series("rhr"),
        series("hrv"), series("rr"), series("inactive"),
    )

    # Skin temperature deviation (°C)
    tz = _z(night.temp, temp_b)
    tp = 0
    if night.temp is not None:
        if night.temp >= 0.45 or (tz is not None and tz >= 2.5):
            tp = 2
        elif night.temp >= 0.25 or (tz is not None and tz >= 1.5):
            tp = 1
    add("temp", night.temp, temp_b, tp)

    # Temperature trend deviation
    trz = _z(night.trend, trend_b)
    trp = 0
    if night.trend is not None:
        if night.trend >= 0.25 or (trz is not None and trz >= 2.5):
            trp = 2
        elif trz is not None and trz >= 1.5:
            trp = 1
    add("trend", night.trend, trend_b, trp)

    # Resting HR ↑
    rz = _z(night.rhr, rhr_b)
    rp = 0
    if night.rhr is not None:
        med = _median(rhr_b) if rhr_b else None
        if (rz is not None and rz >= 1.75) or (med is not None and night.rhr >= med + 7):
            rp = 2
        elif (rz is not None and rz >= 1.25) or (med is not None and night.rhr >= med + 3):
            rp = 1
    add("rhr", night.rhr, rhr_b, rp)

    # HRV ↓
    hz = _z(night.hrv, hrv_b)
    hp = 0
    if night.hrv is not None:
        med = _median(hrv_b) if hrv_b else None
        if (hz is not None and hz <= -1.75) or (med and night.hrv <= med * 0.75):
            hp = 2
        elif (hz is not None and hz <= -1.25) or (med and night.hrv <= med * 0.90):
            hp = 1
    add("hrv", night.hrv, hrv_b, hp)

    # Respiratory rate ↑
    rrz = _z(night.rr, rr_b)
    rrp = 0
    if night.rr is not None:
        med = _median(rr_b) if rr_b else None
        if (rrz is not None and rrz >= 2.0) or (med is not None and night.rr >= med + 1.5):
            rrp = 2
        elif (rrz is not None and rrz >= 1.5) or (med is not None and night.rr >= med + 1.0):
            rrp = 1
    add("rr", night.rr, rr_b, rrp)

    # Previous-day sedentary time ↑
    iz = _z(night.inactive, ina_b)
    ip = 0
    if night.inactive is not None and iz is not None:
        if iz >= 1.75:
            ip = 2
        elif iz >= 1.0:
            ip = 1
    add("inactive", night.inactive, ina_b, ip)

    fired = [c for c in contrib if c["points"] > 0]
    level = _level(score, len(fired), ok)

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
