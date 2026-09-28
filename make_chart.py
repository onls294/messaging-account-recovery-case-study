"""Draw the phone number's daily quality rating as a hand-written SVG (standard library only).

    python make_chart.py        -> quality_series.svg
"""
import csv
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
COLORS = {"GREEN": "#2e9d5b", "YELLOW": "#e3b23c", "RED": "#c8453b"}
LEVEL = {"GREEN": 3, "YELLOW": 2, "RED": 1}
# Dated events. Labels describe what happened, not what caused the rating to move.
EVENTS = [
    ("2026-08-12", "anti-saturation change; retry loop starts"),
    ("2026-08-17", "retry loop cut"),
    ("2026-08-19", "first green"),
    ("2026-08-26", "deploy: retries for provider-refused messages"),
    ("2026-09-03", "red again"),
    ("2026-09-04", "green again"),
    ("2026-09-07", "cadence cap (PR #100)"),
]
W, H, LEFT, TOP, BAR_H = 1000, 340, 70, 56, 150


def load(path=HERE / "data" / "quality_series.csv"):
    with open(path, newline="", encoding="utf-8") as f:
        return [(date.fromisoformat(r["date"]), r["quality_rating"]) for r in csv.DictReader(f)]


def svg(rows, events=EVENTS):
    first, n = rows[0][0], len(rows)
    step = (W - LEFT - 30) / n
    x = lambda d: LEFT + (d - first).days * step
    base = TOP + BAR_H
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif" font-size="12">',
           f'<title>WhatsApp number quality rating, daily, {rows[0][0]} to {rows[-1][0]}</title>',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
           f'<text x="{LEFT}" y="20" font-size="15" font-weight="bold">Phone number quality rating, one bar per day '
           f'({n} days)</text>']
    for label, lvl in LEVEL.items():
        y = base - lvl * BAR_H / 3
        out.append(f'<text x="{LEFT - 8}" y="{y + BAR_H / 6 + 4:.1f}" text-anchor="end" fill="#444">{label.lower()}</text>')
    for d, q in rows:
        h = LEVEL[q] * BAR_H / 3
        out.append(f'<rect x="{x(d):.1f}" y="{base - h:.1f}" width="{step - 1:.1f}" height="{h:.1f}" fill="{COLORS[q]}">'
                   f'<title>{d} {q}</title></rect>')
    for d in (r[0] for r in rows if r[0].day in (1, 11, 21)):
        out.append(f'<text x="{x(d):.1f}" y="{base + 16}" fill="#444">{d:%b %d}</text>')
    for i, (ds, label) in enumerate(events, 1):
        d = date.fromisoformat(ds)
        cx = x(d) + step / 2
        out.append(f'<line x1="{cx:.1f}" y1="{TOP + 4}" x2="{cx:.1f}" y2="{base}" stroke="#222" stroke-dasharray="3,3"/>')
        out.append(f'<circle cx="{cx:.1f}" cy="{TOP - 4}" r="8" fill="#222"/>')
        out.append(f'<text x="{cx:.1f}" y="{TOP}" text-anchor="middle" fill="#fff" font-size="11">{i}</text>')
        col, row = divmod(i - 1, 4)
        out.append(f'<text x="{LEFT + col * 440}" y="{base + 50 + row * 22}" fill="#222">'
                   f'<tspan font-weight="bold">{i}</tspan>  {d:%b %d}: {label}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    rows = load()
    (HERE / "quality_series.svg").write_text(svg(rows), encoding="utf-8")
    print("written: quality_series.svg,", len(rows), "days")
