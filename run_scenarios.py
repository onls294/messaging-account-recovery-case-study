"""Run every scenario in scenarios.py against detector.py and report pass/fail.

    python run_scenarios.py              # run
    python run_scenarios.py --markdown   # rewrite the scenario table in EVAL-DESIGN.md
"""
import sys

from detector import detect
from scenarios import PENDING, SCENARIOS, historical_series


def check(sid, sc, history_alerts):
    if sc["source"] == "historical":
        if sc["date"] == "*":
            got = len(history_alerts)
        else:
            got = [a for d, a in history_alerts if d == sc["date"]]
        return got == sc["expected"], got
    try:
        got = detect(sc["input"])
    except Exception as e:  # a scenario may expect a specific error; any other error is a failure
        return sc["raises"] is not None and isinstance(e, sc["raises"]), type(e).__name__
    return sc["raises"] is None and got == sc["expected"], got


def run():
    history = detect(historical_series())
    return {sid: check(sid, sc, history) for sid, sc in SCENARIOS.items()}


def markdown_table(results):
    lines = ["| id | source | input | expected | why | result |", "|---|---|---|---|---|---|"]
    for sid, sc in SCENARIOS.items():
        if sc["source"] == "historical":
            inp = "real series, whole run" if sc["date"] == "*" else f"real series, alerts on {sc['date']}"
            exp = f"{sc['expected']} alerts" if sc["date"] == "*" else (", ".join(sc["expected"]) or "none")
        else:
            rows = sc["input"]
            inp = " ".join(r["rating"][0] for r in rows) or "empty"
            if rows and "blocked" in rows[0]:
                inp += f"; blocked/accepted {rows[0]['blocked']}/{rows[0]['accepted']} ... {rows[-1]['blocked']}/{rows[-1]['accepted']}"
            exp = sc["raises"].__name__ if sc["raises"] else (", ".join(f"day {int(d[-2:]) - 1}: {a}" for d, a in sc["expected"]) or "none")
        lines.append(f"| {sid} | {sc['source']} | {inp} | {exp} | {sc['why']} | {'pass' if results[sid][0] else 'FAIL'} |")
    lines += ["", "**Pending (historical, need per-day counts):**", ""]
    lines += [f"- **{pid}** ({day}): {text}" for pid, day, text in PENDING]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    results = run()
    if "--markdown" in sys.argv:
        from pathlib import Path
        doc = Path(__file__).resolve().parent / "EVAL-DESIGN.md"
        head = doc.read_text(encoding="utf-8").split("<!-- scenarios -->")[0]
        doc.write_text(head + "<!-- scenarios -->\n\n" + markdown_table(results), encoding="utf-8")
    for sid, (ok, got) in results.items():
        print(f"{'PASS' if ok else 'FAIL'} {sid} [{SCENARIOS[sid]['source']}]" + ("" if ok else f" got {got}"))
    n_ok = sum(ok for ok, _ in results.values())
    print(f"\n{n_ok}/{len(results)} passed; {len(PENDING)} historical scenarios pending (need per-day counts)")
    sys.exit(0 if n_ok == len(results) else 1)
