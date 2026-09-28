"""python -m unittest -v"""
import unittest

import make_chart
from detector import detect
from run_scenarios import run
from scenarios import SCENARIOS, historical_series


class Scenarios(unittest.TestCase):
    def test_every_scenario_passes(self):
        failed = {sid: got for sid, (ok, got) in run().items() if not ok}
        self.assertEqual(failed, {})

    def test_scenario_count_is_within_the_design(self):
        self.assertTrue(30 <= len(SCENARIOS) <= 50)

    def test_negative_a_wrong_expectation_fails(self):
        # The harness must be able to fail: flip one expectation and it has to show up.
        sc = dict(SCENARIOS["S03"], expected=[])
        self.assertNotEqual(detect(sc["input"]), sc["expected"])


class Data(unittest.TestCase):
    def test_series_has_only_date_and_rating(self):
        rows = historical_series()
        self.assertEqual(len(rows), 48)
        self.assertEqual({r["rating"] for r in rows}, {"GREEN", "YELLOW", "RED"})

    def test_chart_has_one_bar_per_day_and_every_event(self):
        out = make_chart.svg(make_chart.load())
        self.assertEqual(out.count("<rect ") - 1, 48)  # minus the background
        self.assertEqual(out.count("<circle "), len(make_chart.EVENTS))


if __name__ == "__main__":
    unittest.main()
