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
    """Healthy baseline nights ending before `base` (default: yesterday-3)."""
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
                sleep_s=kw.get("sleep_s", 7.5 * 3600),
                rem_s=kw.get("rem_s", 90 * 60),
            )
        )
    return out


class ScoreNightTest(unittest.TestCase):
    def test_insufficient_data(self):
        day = date(2026, 7, 20)
        night = Night(day=day, temp=0.6, rhr=60, hrv=40, rr=15)
        r = score_night(night, [])
        self.assertEqual(r["level"], "insufficient_data")

    def test_none_healthy(self):
        day = date(2026, 7, 20)
        hist = _hist(20, base=day)
        # Fill last 14d gate with healthy nights adjacent
        for i in range(10):
            hist.append(
                Night(
                    day=day - timedelta(days=10 - i),
                    temp=0.0, rhr=55, hrv=50, rr=14,
                    inactive=36000, sleep_s=7.5 * 3600, rem_s=90 * 60,
                )
            )
        night = Night(day=day, temp=0.0, rhr=55, hrv=50, rr=14, inactive=36000,
                      sleep_s=7.5 * 3600, rem_s=90 * 60)
        r = score_night(night, hist)
        self.assertEqual(r["level"], "none")
        self.assertLessEqual(r["score"], 1)

    def test_temp_only_strong_is_minor(self):
        day = date(2026, 7, 20)
        hist = _hist(20, base=day)
        for i in range(10):
            hist.append(
                Night(
                    day=day - timedelta(days=10 - i),
                    temp=0.0, rhr=55, hrv=50, rr=14,
                    inactive=36000, sleep_s=7.5 * 3600, rem_s=90 * 60,
                )
            )
        night = Night(day=day, temp=0.55, rhr=55, hrv=50, rr=14, inactive=36000,
                      sleep_s=7.5 * 3600, rem_s=90 * 60)
        r = score_night(night, hist)
        self.assertEqual(r["level"], "minor")
        self.assertEqual(r["score"], 2)

    def test_major_multi_signal(self):
        day = date(2026, 7, 20)
        hist = _hist(20, base=day)
        for i in range(10):
            hist.append(
                Night(
                    day=day - timedelta(days=10 - i),
                    temp=0.0, rhr=55, hrv=50, rr=14,
                    inactive=36000, sleep_s=7.5 * 3600, rem_s=90 * 60,
                )
            )
        night = Night(
            day=day, temp=0.55, rhr=65, hrv=35, rr=16.5,
            inactive=36000, sleep_s=7.5 * 3600, rem_s=90 * 60,
        )
        r = score_night(night, hist)
        self.assertEqual(r["level"], "major")
        self.assertGreaterEqual(r["score"], 3)
        self.assertEqual(r["algorithm_version"], "v1")
        self.assertEqual(r["summary_text"], "Major Signs")


if __name__ == "__main__":
    unittest.main()
