"""Paper-trade the scanner's candidates with capped position sizing, and
log every simulated trade so the model can be checked against reality
once markets actually resolve."""
import csv
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")
from scanner import scan  # noqa: E402

LOG_PATH = os.path.join(os.path.dirname(__file__), "paper_trades.csv")
BANKROLL = 10_000.0
MAX_POSITION_PCT = 0.05  # never risk more than 5% of bankroll on one market
MIN_DAYS_TO_RESOLUTION = 0.5  # skip markets resolving in <12h, too noisy to size sanely
MIN_ORDER_SIZE = 5.0  # below this isn't worth logging as a position
FIELDS = [
    "logged_at", "slug", "question", "outcome", "price",
    "days_to_resolution", "raw_return_pct", "position_size", "status",
    "pnl",
]


def size_position(candidate, bankroll):
    # Confidence-weighted, hard-capped. Price itself is treated as the
    # market's own confidence estimate (this is naive on purpose --
    # replace with an independent probability model before risking real money).
    confidence = candidate["price"]
    kelly_fraction = confidence - (1 - confidence)  # simplified edge estimate
    size = bankroll * min(max(kelly_fraction, 0), 1) * MAX_POSITION_PCT
    return round(min(size, bankroll * MAX_POSITION_PCT), 2)


def existing_rows():
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, newline="") as f:
        return list(csv.DictReader(f))


def available_balance(rows, bankroll=BANKROLL):
    """Real remaining capital: bankroll +/- realized pnl, minus whatever's
    still tied up in open positions. Prevents sizing every new trade off a
    static bankroll as if closed capital is instantly available again."""
    realized_pnl = sum(float(r["pnl"]) for r in rows if r["status"] in ("win", "loss") and r["pnl"])
    open_exposure = sum(float(r["position_size"]) for r in rows if r["status"] == "open")
    return bankroll + realized_pnl - open_exposure


def log_trades(candidates, bankroll=BANKROLL):
    rows = existing_rows()
    is_new = not rows
    seen = {r["slug"] for r in rows}
    balance = available_balance(rows, bankroll)

    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        for c in candidates:
            if c["slug"] in seen:
                continue
            if c["days_to_resolution"] < MIN_DAYS_TO_RESOLUTION:
                continue
            if balance < MIN_ORDER_SIZE:
                break  # out of capital -- stop opening new positions this run
            size = min(size_position(c, bankroll), balance)
            if size < MIN_ORDER_SIZE:
                continue
            balance -= size
            writer.writerow({
                "logged_at": datetime.now(timezone.utc).isoformat(),
                "slug": c["slug"],
                "question": c["question"],
                "outcome": c["outcome"],
                "price": c["price"],
                "days_to_resolution": c["days_to_resolution"],
                "raw_return_pct": c["raw_return_pct"],
                "position_size": size,
                "status": "open",
                "pnl": "",
            })


if __name__ == "__main__":
    candidates = scan()
    log_trades(candidates)
    print(f"Logged candidates to {LOG_PATH}")
