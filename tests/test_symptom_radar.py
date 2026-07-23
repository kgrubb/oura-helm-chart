#!/usr/bin/env python3
"""Boundary tests for Symptom Radar scoring."""
from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "charts" / "oura" / "files"))
from symptom_radar import Night, score_night  # noqa: E402


def _hist(n: int = 20, base: date | None = None, **kw) -> list[Night]:
    end = (base or date.today()) - timedelta(days=4)
    out = []
    for i in range(n):
        d = end - timedelta(days=n - 1 - i)
        out.append(
            Night(
                day=d,
                temp=kw.get("temp", 0.0),
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
                temp=0.0, rhr=55, hrv=50, rr=14, inactive=36000,
            )
        )


class ScoreNightTest(unittest.TestCase):
    def test_insufficient_data(self):
        day = date(2026, 7, 20)
        night = Night(day=day, temp=0.6, rhr=60, hrv=40, rr=15)
        self.assertEqual(score_night(night, [])["level"], "insufficient_data")

    def test_none_healthy(self):
        day = date(2026, 7, 20)
        hist = _hist(20, base=day)
        _fill_gate(hist, day)
        night = Night(day=day, temp=0.0, rhr=55, hrv=50, rr=14, inactive=36000)
        r = score_night(night, hist)
        self.assertEqual(r["level"], "none")
        self.assertEqual(r["algorithm_version"], "v2")

    def test_mild_noise_is_none(self):
        """Jul-22-style: several weak z≈1 deviations must not page."""
        day = date(2026, 7, 20)
        hist = _hist(20, base=day)
        _fill_gate(hist, day)
        night = Night(day=day, temp=0.3, rhr=60, hrv=47, rr=15.0, inactive=36000)
        r = score_night(night, hist)
        self.assertEqual(r["level"], "none")

    def test_temp_only_strong_is_minor(self):
        day = date(2026, 7, 20)
        hist = _hist(20, base=day)
        _fill_gate(hist, day)
        night = Night(day=day, temp=0.65, rhr=55, hrv=50, rr=14, inactive=36000)
        r = score_night(night, hist)
        self.assertEqual(r["level"], "minor")
        self.assertEqual(r["score"], 2)

    def test_major_multi_signal(self):
        day = date(2026, 7, 20)
        hist = _hist(20, base=day)
        _fill_gate(hist, day)
        night = Night(day=day, temp=0.65, rhr=70, hrv=30, rr=17.0, inactive=36000)
        r = score_night(night, hist)
        self.assertEqual(r["level"], "major")
        self.assertGreaterEqual(r["score"], 4)
        self.assertEqual(r["summary_text"], "Major signs")


if __name__ == "__main__":
    unittest.main()
