# Evaluation design: a phone-number health monitor

What a monitor for a WhatsApp Business phone number should flag, written as scenarios with the
expected output before any code ran. `detector.py` is a generic rule-based monitor built to
pass them; `run_scenarios.py` runs them all.

## What is being evaluated

A daily monitor that reads two things:

1. **The provider's quality rating** (GREEN / YELLOW / RED), once a day.
2. **Optionally, the system's own throttle counts:** attempts the CRM blocked itself, and
   messages the provider accepted.

It answers one question each day: *does someone need to look at the number today?*

## Design rules

- **Rates, not counts.** The throttle alert is blocked **per accepted message**. A raw count
  fires whenever volume moves, which says nothing about health (S01, S02).
- **Silence must be explained.** When there is too little volume to judge the rate, the monitor
  says `low_volume` instead of staying quiet (S05, S06). A missing day is reported (S22).
- **Bad input stops the run.** An unknown rating, out-of-order or duplicate dates raise an error
  instead of being guessed (S19–S21).
- **Improvements are not alerts.** Only drops, red days, long non-green streaks and recoveries
  are (H03).
- **The rating cannot attribute.** A daily rating cannot see a same-day regression (H08) and says
  nothing about a change made while it was already green (H13).

## Sources

- **historical:** the real daily rating series, 48 days from 2026-08-11 to 2026-09-27
  (`data/quality_series.csv`: date and rating only). Each scenario checks the alerts on one date.
- **synthetic:** invented series, dates starting 2026-01-01. **No value comes from a real
  account.**
- **pending:** historical scenarios that need per-day throttle counts. Those counts exist but
  not in a publishable form, so the scenarios are designed and not run.

## Circularity

**The same author wrote the detector and the expected results.** Every expected output was
fixed by hand before the detector ran. Still, 42 of 42 only measures that the detector meets
this specification. It does not show that the specification is good: a rule the author did not
think of is missing from both. **Next step:** an independent validation, with scenarios or
expected alerts written by someone who has not seen the detector.

## Known limitation

A slow drift never crosses a threshold relative to a rolling median (S09). Catching it needs a
fixed reference period, which is the next rule to add.

## Scenarios

Regenerate this table with `python run_scenarios.py --markdown`. In the synthetic rows, `G Y R`
is one rating per day and "day N" counts from 0.

<!-- scenarios -->

| id | source | input | expected | why | result |
|---|---|---|---|---|---|
| H01 | historical | real series, alerts on 2026-08-11 | red | First row is RED with no previous day, so no rating_down. Open question: this red is earlier than the Aug 12 change that started the retry loop. | pass |
| H02 | historical | real series, alerts on 2026-08-12 | red | RED again: red alerts every red day; staying red is not a drop. | pass |
| H03 | historical | real series, alerts on 2026-08-13 | none | RED to YELLOW is an improvement; improvements are not alerts. | pass |
| H04 | historical | real series, alerts on 2026-08-16 | none | 6th consecutive non-green day: below the 7-day streak. | pass |
| H05 | historical | real series, alerts on 2026-08-17 | not_green_streak | 7th consecutive non-green day. It is also the day the loop was cut. | pass |
| H06 | historical | real series, alerts on 2026-08-18 | none | The streak alert fires once per streak, not every day after. | pass |
| H07 | historical | real series, alerts on 2026-08-19 | recovered | First green after the red and yellow run. | pass |
| H08 | historical | real series, alerts on 2026-08-26 | none | Deploy day: the rating is still green. A daily rating cannot see a same-day regression. | pass |
| H09 | historical | real series, alerts on 2026-08-27 | rating_down | GREEN to YELLOW: the relapse. | pass |
| H10 | historical | real series, alerts on 2026-09-02 | not_green_streak | 7th consecutive yellow day of the relapse. | pass |
| H11 | historical | real series, alerts on 2026-09-03 | red, rating_down | YELLOW to RED. | pass |
| H12 | historical | real series, alerts on 2026-09-04 | recovered | Back to green; the recovery matches no deploy of this project. | pass |
| H13 | historical | real series, alerts on 2026-09-07 | none | Cadence-cap day (PR #100): the number was already green. The rating says nothing about it. | pass |
| H14 | historical | real series, whole run | 9 alerts | Whole series: exactly the alerts listed above, and none after Sep 4. | pass |
| S01 | synthetic | G G G G G G G G G G G G G G G; blocked/accepted 50/100 ... 25/50 | none | Volume halves, blocked per accepted stays 0.5: no alert. A raw-count threshold would have fired. | pass |
| S02 | synthetic | G G G G G G G G G G G G; blocked/accepted 50/100 ... 150/300 | none | Volume triples at the same rate: no alert. | pass |
| S03 | synthetic | G G G G G G G G; blocked/accepted 50/100 ... 100/100 | day 7: blocked_rate_spike | Rate doubles at the same volume: 1.0 > 1.5 x 0.5. | pass |
| S04 | synthetic | G G G G G G G G; blocked/accepted 50/100 ... 75/100 | none | Rate at exactly 1.5x the median: the rule is strictly greater. | pass |
| S05 | synthetic | G G G G G G G G; blocked/accepted 50/100 ... 10/10 | day 7: low_volume | Rate 1.0 but only 10 accepted: too few to judge, and the monitor says so. | pass |
| S06 | synthetic | G G G G G; blocked/accepted 50/100 ... 30/0 | day 4: low_volume | 0 accepted: no division by zero, low_volume instead. | pass |
| S07 | synthetic | G G G; blocked/accepted 50/100 ... 200/100 | none | Only 2 previous days: no baseline yet, no spike. | pass |
| S08 | synthetic | G G G G; blocked/accepted 50/100 ... 200/100 | day 3: blocked_rate_spike | 3 previous days are enough for a baseline. | pass |
| S09 | synthetic | G G G G G G G G G G G G G G; blocked/accepted 500/1000 ... 1726/1000 | none | Slow creep of 10 % a day never crosses 1.5x a trailing median. Known limitation: a drift needs a fixed reference, not a rolling one. | pass |
| S10 | synthetic | G G G G G G G G G G; blocked/accepted 50/100 ... 50/100 | day 7: blocked_rate_spike | One-day spike, then normal: one alert; the median ignores the outlier afterwards. | pass |
| S11 | synthetic | G G G G G G G G; blocked/accepted 50/100 ... 200/100 | day 7: blocked_rate_spike | Throttle spike while the rating is still green: the counts lead the rating. | pass |
| S12 | synthetic | G G Y | day 2: rating_down | No counts at all: rating-only alerts still work. | pass |
| S25 | synthetic | G G G G G G; blocked/accepted 0/100 ... 5/100 | day 5: blocked_rate_spike | After a week with 0 blocked, any throttling alerts (median 0). Deliberate: a clean baseline makes the first blocks news. | pass |
| S13 | synthetic | G R | day 1: red, day 1: rating_down | GREEN straight to RED. | pass |
| S14 | synthetic | Y R | day 1: red, day 1: rating_down | YELLOW to RED. | pass |
| S15 | synthetic | R Y R | day 0: red, day 2: red, day 2: rating_down | Red, better, red again. | pass |
| S16 | synthetic | Y Y Y Y Y Y G | day 6: recovered | 6 non-green days then green: recovered, no streak. | pass |
| S17 | synthetic | Y Y Y Y Y Y Y Y Y Y Y Y Y Y | day 6: not_green_streak | 14 non-green days: the streak alert fires once, on day 7. | pass |
| S18 | synthetic | G Y G | day 1: rating_down, day 2: recovered | One yellow day. | pass |
| S26 | synthetic | R G | day 0: red, day 1: recovered | First row RED: red only, no drop. | pass |
| S27 | synthetic | Y Y Y Y Y Y G Y Y Y Y Y Y Y | day 6: recovered, day 7: rating_down, day 13: not_green_streak | A green day resets the streak; the new streak alerts on its own 7th day. | pass |
| S19 | synthetic | O | ValueError | Unknown rating: stop, do not guess. | pass |
| S20 | synthetic | G G | ValueError | Dates out of order: stop. | pass |
| S21 | synthetic | G G | ValueError | Duplicate date: stop. | pass |
| S22 | synthetic | G G | day 3: missing_day | Two missing days: the gap is reported, not silently skipped. | pass |
| S23 | synthetic | empty | none | Empty input: no alerts. | pass |
| S24 | synthetic | G | none | One green day: nothing to compare. | pass |
| S28 | synthetic | G G; blocked/accepted 50/100 ... None/None | none | Counts missing on one day: that day is rating-only. | pass |

**Pending (historical, need per-day counts):**

- **P01** (2026-08-12): blocked_rate_spike expected: throttle blocks jump when the retry loop starts.
- **P02** (2026-08-18): no spike expected; blocked per accepted should fall the day after the loop cut.
- **P03** (2026-08-27): blocked_rate_spike expected: the relapse the day after the Aug 26 deploy.
- **P04** (2026-09-07): blocked per accepted, 7 days each side of PR #100: a change is expected but cannot be attributed to #100 alone (other PRs in the same window).
- **P05** (2026-08-20): counting by flow is impossible before the flow column was filled; the detector must use counts that do not depend on it.
