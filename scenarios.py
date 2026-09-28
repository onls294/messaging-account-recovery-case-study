"""Evaluation scenarios for detector.py. Every expected output was written by hand from the
rule, before running the detector.

historical  run on data/quality_series.csv (the real daily rating); `expected` are the alerts
            on one date of the full run.
synthetic   invented series (dates start 2026-01-01, ids S..); `expected` is the full output.
            SYNTHETIC: no value comes from a real account.
"""
import csv
from datetime import date, timedelta
from pathlib import Path

SERIES = Path(__file__).resolve().parent / "data" / "quality_series.csv"


def historical_series(path=SERIES):
    with open(path, newline="", encoding="utf-8") as f:
        return [{"date": r["date"], "rating": r["quality_rating"]} for r in csv.DictReader(f)]


def D(i):
    return str(date(2026, 1, 1) + timedelta(days=i))


def S(ratings, blocked=None, accepted=None):
    """Synthetic series: ratings as a string (G/Y/R per day) or list; counts as lists or None."""
    names = {"G": "GREEN", "Y": "YELLOW", "R": "RED"}
    rows = []
    for i, q in enumerate(ratings):
        row = {"date": D(i), "rating": names.get(q, q)}
        if blocked is not None:
            row.update(blocked=blocked[i], accepted=accepted[i])
        rows.append(row)
    return rows


def H(day, expected, why):
    return {"source": "historical", "date": day, "expected": expected, "why": why}


def Y(input_, expected, why, raises=None):
    return {"source": "synthetic", "input": input_, "expected": expected, "why": why, "raises": raises}


SCENARIOS = {
    # --- historical: the real rating series, 2026-08-11 to 2026-09-27 ---
    "H01": H("2026-08-11", ["red"], "First row is RED with no previous day, so no rating_down. Open question: this red is "
             "earlier than the Aug 12 change that started the retry loop."),
    "H02": H("2026-08-12", ["red"], "RED again: red alerts every red day; staying red is not a drop."),
    "H03": H("2026-08-13", [], "RED to YELLOW is an improvement; improvements are not alerts."),
    "H04": H("2026-08-16", [], "6th consecutive non-green day: below the 7-day streak."),
    "H05": H("2026-08-17", ["not_green_streak"], "7th consecutive non-green day. It is also the day the loop was cut."),
    "H06": H("2026-08-18", [], "The streak alert fires once per streak, not every day after."),
    "H07": H("2026-08-19", ["recovered"], "First green after the red and yellow run."),
    "H08": H("2026-08-26", [], "Deploy day: the rating is still green. A daily rating cannot see a same-day regression."),
    "H09": H("2026-08-27", ["rating_down"], "GREEN to YELLOW: the relapse."),
    "H10": H("2026-09-02", ["not_green_streak"], "7th consecutive yellow day of the relapse."),
    "H11": H("2026-09-03", ["red", "rating_down"], "YELLOW to RED."),
    "H12": H("2026-09-04", ["recovered"], "Back to green; the recovery matches no deploy of this project."),
    "H13": H("2026-09-07", [], "Cadence-cap day (PR #100): the number was already green. The rating says nothing about it."),
    "H14": H("*", 9, "Whole series: exactly the alerts listed above, and none after Sep 4."),

    # --- synthetic: volume vs. rate ---
    "S01": Y(S("G" * 15, [50] * 10 + [25] * 5, [100] * 10 + [50] * 5), [],
             "Volume halves, blocked per accepted stays 0.5: no alert. A raw-count threshold would have fired."),
    "S02": Y(S("G" * 12, [50] * 8 + [150] * 4, [100] * 8 + [300] * 4), [],
             "Volume triples at the same rate: no alert."),
    "S03": Y(S("G" * 8, [50] * 7 + [100], [100] * 8), [(D(7), "blocked_rate_spike")],
             "Rate doubles at the same volume: 1.0 > 1.5 x 0.5."),
    "S04": Y(S("G" * 8, [50] * 7 + [75], [100] * 8), [],
             "Rate at exactly 1.5x the median: the rule is strictly greater."),
    "S05": Y(S("G" * 8, [50] * 7 + [10], [100] * 7 + [10]), [(D(7), "low_volume")],
             "Rate 1.0 but only 10 accepted: too few to judge, and the monitor says so."),
    "S06": Y(S("G" * 5, [50] * 4 + [30], [100] * 4 + [0]), [(D(4), "low_volume")],
             "0 accepted: no division by zero, low_volume instead."),
    "S07": Y(S("GGG", [50, 50, 200], [100, 100, 100]), [],
             "Only 2 previous days: no baseline yet, no spike."),
    "S08": Y(S("GGGG", [50, 50, 50, 200], [100] * 4), [(D(3), "blocked_rate_spike")],
             "3 previous days are enough for a baseline."),
    "S09": Y(S("G" * 14, [round(500 * 1.1 ** k) for k in range(14)], [1000] * 14), [],
             "Slow creep of 10 % a day never crosses 1.5x a trailing median. Known limitation: a drift needs "
             "a fixed reference, not a rolling one."),
    "S10": Y(S("G" * 10, [50] * 7 + [150, 50, 50], [100] * 10), [(D(7), "blocked_rate_spike")],
             "One-day spike, then normal: one alert; the median ignores the outlier afterwards."),
    "S11": Y(S("G" * 8, [50] * 7 + [200], [100] * 8), [(D(7), "blocked_rate_spike")],
             "Throttle spike while the rating is still green: the counts lead the rating."),
    "S12": Y(S("GGY"), [(D(2), "rating_down")], "No counts at all: rating-only alerts still work."),
    "S25": Y(S("G" * 6, [0] * 5 + [5], [100] * 6), [(D(5), "blocked_rate_spike")],
             "After a week with 0 blocked, any throttling alerts (median 0). Deliberate: a clean baseline "
             "makes the first blocks news."),

    # --- synthetic: rating transitions ---
    "S13": Y(S("GR"), [(D(1), "red"), (D(1), "rating_down")], "GREEN straight to RED."),
    "S14": Y(S("YR"), [(D(1), "red"), (D(1), "rating_down")], "YELLOW to RED."),
    "S15": Y(S("RYR"), [(D(0), "red"), (D(2), "red"), (D(2), "rating_down")], "Red, better, red again."),
    "S16": Y(S("YYYYYYG"), [(D(6), "recovered")], "6 non-green days then green: recovered, no streak."),
    "S17": Y(S("Y" * 14), [(D(6), "not_green_streak")], "14 non-green days: the streak alert fires once, on day 7."),
    "S18": Y(S("GYG"), [(D(1), "rating_down"), (D(2), "recovered")], "One yellow day."),
    "S26": Y(S("RG"), [(D(0), "red"), (D(1), "recovered")], "First row RED: red only, no drop."),
    "S27": Y(S("Y" * 6 + "G" + "Y" * 7), [(D(6), "recovered"), (D(7), "rating_down"), (D(13), "not_green_streak")],
             "A green day resets the streak; the new streak alerts on its own 7th day."),

    # --- synthetic: input problems ---
    "S19": Y(S(["ORANGE"]), None, "Unknown rating: stop, do not guess.", raises=ValueError),
    "S20": Y([{"date": D(1), "rating": "GREEN"}, {"date": D(0), "rating": "GREEN"}], None,
             "Dates out of order: stop.", raises=ValueError),
    "S21": Y([{"date": D(0), "rating": "GREEN"}, {"date": D(0), "rating": "GREEN"}], None,
             "Duplicate date: stop.", raises=ValueError),
    "S22": Y([{"date": D(0), "rating": "GREEN"}, {"date": D(3), "rating": "GREEN"}], [(D(3), "missing_day")],
             "Two missing days: the gap is reported, not silently skipped."),
    "S23": Y([], [], "Empty input: no alerts."),
    "S24": Y(S("G"), [], "One green day: nothing to compare."),
    "S28": Y(S("GG", [50, None], [100, None]), [], "Counts missing on one day: that day is rating-only."),
}

# Historical scenarios that need per-day counts. The counts exist, but not in publishable form,
# so these are designed and not run here.
PENDING = [
    ("P01", "2026-08-12", "blocked_rate_spike expected: throttle blocks jump when the retry loop starts."),
    ("P02", "2026-08-18", "no spike expected; blocked per accepted should fall the day after the loop cut."),
    ("P03", "2026-08-27", "blocked_rate_spike expected: the relapse the day after the Aug 26 deploy."),
    ("P04", "2026-09-07", "blocked per accepted, 7 days each side of PR #100: a change is expected but cannot be "
                          "attributed to #100 alone (other PRs in the same window)."),
    ("P05", "2026-08-20", "counting by flow is impossible before the flow column was filled; the detector must "
                          "use counts that do not depend on it."),
]
