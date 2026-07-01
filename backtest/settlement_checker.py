"""Check paper_trades.csv against live market state and mark each row
win/loss/open once its market has actually resolved."""
import csv
import os
import sys

sys.path.insert(0, "../data")
from gamma_client import GAMMA_URL  # noqa: E402
import requests  # noqa: E402

LOG_PATH = os.path.join(os.path.dirname(__file__), "paper_trades.csv")
FIELDS = [
    "logged_at", "slug", "question", "outcome", "price",
    "days_to_resolution", "raw_return_pct", "position_size", "status",
    "pnl",
]


def get_market_by_slug(slug):
    resp = requests.get(f"{GAMMA_URL}/markets", params={"slug": slug}, timeout=10)
    resp.raise_for_status()
    results = resp.json()
    return results[0] if results else None


def check_settlements():
    if not os.path.exists(LOG_PATH):
        print("No paper_trades.csv yet -- run paper_trader.py first.")
        return

    with open(LOG_PATH) as f:
        rows = list(csv.DictReader(f))

    updated = 0
    for row in rows:
        if row.get("status") not in ("open", None, ""):
            continue  # already settled

        market = get_market_by_slug(row["slug"])
        if not market or not market.get("closed"):
            row.setdefault("pnl", "")
            continue

        import json
        outcomes = json.loads(market["outcomes"])
        prices = json.loads(market["outcomePrices"])
        final = dict(zip(outcomes, prices))
        won = float(final.get(row["outcome"], 0)) >= 0.5

        size = float(row["position_size"])
        entry_price = float(row["price"])
        if won:
            pnl = size * (1 - entry_price) / entry_price
            row["status"] = "win"
        else:
            pnl = -size
            row["status"] = "loss"
        row["pnl"] = round(pnl, 2)
        updated += 1

    for row in rows:
        row.setdefault("pnl", "")

    with open(LOG_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Checked {len(rows)} rows, settled {updated} this run.")


if __name__ == "__main__":
    check_settlements()
