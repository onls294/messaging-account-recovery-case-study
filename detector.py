"""A generic health monitor for a messaging phone number (standard library only).

Input: one row per day, in date order, with the provider's quality rating and, optionally,
how many send attempts the system's own throttle blocked and how many messages the provider
accepted. Output: a list of (date, alert) pairs.

Alerts
    red                 the rating is RED today
    rating_down         the rating is lower than yesterday's
    recovered           back to GREEN after at least one non-green day
    not_green_streak    the 7th consecutive non-green day (once per streak)
    blocked_rate_spike  blocked per accepted today is more than 1.5x the median of the
                        previous 7 days (needs at least 3 of them)
    low_volume          fewer than 20 accepted: the rate is not judged today
    missing_day         a calendar day is missing before this row

The throttle alert is written per accepted message, never as a raw count: a raw threshold
fires on any change in volume, not on a failure.
"""
from datetime import date, timedelta
from statistics import median

LEVEL = {"RED": 1, "YELLOW": 2, "GREEN": 3}
WINDOW, RATE_JUMP, MIN_ACCEPTED, STREAK = 7, 1.5, 20, 7


def detect(days):
    alerts, prev, streak, rates = [], None, 0, []
    for d in days:
        day, q = date.fromisoformat(d["date"]), d["rating"]
        if q not in LEVEL:
            raise ValueError(f"{day}: unknown rating {q!r}")
        if prev is not None:
            if day <= prev["day"]:
                raise ValueError(f"{day}: dates must be strictly increasing")
            if day - prev["day"] > timedelta(days=1):
                alerts.append((str(day), "missing_day"))
        if q == "RED":
            alerts.append((str(day), "red"))
        if prev is not None and LEVEL[q] < LEVEL[prev["rating"]]:
            alerts.append((str(day), "rating_down"))
        if q == "GREEN" and streak > 0:
            alerts.append((str(day), "recovered"))
        streak = 0 if q == "GREEN" else streak + 1
        if streak == STREAK:
            alerts.append((str(day), "not_green_streak"))

        blocked, accepted = d.get("blocked"), d.get("accepted")
        if blocked is not None and accepted is not None:
            if accepted < MIN_ACCEPTED:
                alerts.append((str(day), "low_volume"))
            else:
                rate = blocked / accepted
                past = rates[-WINDOW:]
                if len(past) >= 3 and rate > RATE_JUMP * median(past):
                    alerts.append((str(day), "blocked_rate_spike"))
                rates.append(rate)
        prev = {"day": day, "rating": q}
    return alerts
