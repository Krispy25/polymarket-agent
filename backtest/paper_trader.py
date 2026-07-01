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
FIELDS = [
    "logged_at", "slug", "question", "outcome", "price",
    "days_to_resolution", "raw_return_pct", "position_size", "status",
]


def size_position(candidate, bankroll):
    # Confidence-weighted, hard-capped. Price itself is treated as the
    # market's own confidence estimate (this is naive on purpose --
    # replace with an independent probability model before risking real money).
    confidence = candidate["price"]
    kelly_fraction = confidence - (1 - confidence)  # simplified edge estimate
    size = bankroll * min(max(kelly_fraction, 0), 1) * MAX_POSITION_PCT
    return round(min(size, bankroll * MAX_POSITION_PCT), 2)


def log_trades(candidates, bankroll=BANKROLL):
    is_new = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        for c in candidates:
            if c["days_to_resolution"] < MIN_DAYS_TO_RESOLUTION:
                continue
            size = size_position(c, bankroll)
            if size <= 0:
                continue
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
            })


if __name__ == "__main__":
    candidates = scan()
    log_trades(candidates)
    print(f"Logged candidates to {LOG_PATH}")
