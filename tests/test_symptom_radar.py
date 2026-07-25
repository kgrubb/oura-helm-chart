"""Boundary tests for Symptom Radar scoring."""

from __future__ import annotations

from datetime import date, timedelta

from oura_collector.symptom_radar import Night, score_night


def _hist(n: int = 20, base: date | None = None, **kw: float) -> list[Night]:
    end = (base or date.today()) - timedelta(days=4)
    out: list[Night] = []
    for i in range(n):
        day = end - timedelta(days=n - 1 - i)
        out.append(
            Night(
                day=day,
                temp=kw.get("temp", 0.0),
                trend=kw.get("trend", 0.0),
                rhr=kw.get("rhr", 55.0),
                hrv=kw.get("hrv", 50.0),
                rr=kw.get("rr", 14.0),
                inactive=kw.get("inactive", 36000.0),
            )
        )
    return out


def _fill_gate(hist: list[Night], day: date) -> None:
    for i in range(10):
        hist.append(
            Night(
                day=day - timedelta(days=10 - i),
                temp=0.0,
                trend=0.0,
                rhr=55,
                hrv=50,
                rr=14,
                inactive=36000,
            )
        )


def test_insufficient_data() -> None:
    day = date(2026, 7, 20)
    night = Night(day=day, temp=0.6, rhr=60, hrv=40, rr=15)
    assert score_night(night, [])["level"] == "insufficient_data"


def test_none_healthy() -> None:
    day = date(2026, 7, 20)
    hist = _hist(20, base=day)
    _fill_gate(hist, day)
    night = Night(day=day, temp=0.0, trend=0.0, rhr=55, hrv=50, rr=14, inactive=36000)
    result = score_night(night, hist)
    assert result["level"] == "none"
    assert result["summary_text"] == "no signs"
    assert result["algorithm_version"] == "v3"


def test_jul22_style_is_minor() -> None:
    day = date(2026, 7, 20)
    hist = _hist(20, base=day)
    _fill_gate(hist, day)
    night = Night(day=day, temp=0.3, trend=0.11, rhr=60, hrv=45, rr=14, inactive=36000)
    assert score_night(night, hist)["level"] == "minor"


def test_temp_and_trend_major() -> None:
    day = date(2026, 7, 20)
    hist = _hist(20, base=day)
    _fill_gate(hist, day)
    night = Night(day=day, temp=0.45, trend=0.30, rhr=55, hrv=50, rr=14, inactive=36000)
    result = score_night(night, hist)
    assert result["level"] == "major"
    assert result["summary_text"] == "Major signs"
