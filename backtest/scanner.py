"""Screen live Polymarket markets for near-certain outcomes and estimate
the *realistic* annualized return each one actually offers (not 3%/day)."""
import json
import sys
from datetime import datetime, timezone

sys.path.insert(0, "../data")
from gamma_client import get_markets  # noqa: E402

NEAR_CERTAIN_THRESHOLD = 0.95  # price above this = market thinks it's ~certain
MIN_LIQUIDITY = 1000  # ignore markets too thin to size a real position in


def days_to_resolution(end_date_iso):
    end = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return max((end - now).total_seconds() / 86400, 1 / 24)  # floor at 1hr


def score_market(market):
    try:
        prices = json.loads(market["outcomePrices"])
        outcomes = json.loads(market["outcomes"])
    except (KeyError, json.JSONDecodeError):
        return None

    liquidity = float(market.get("liquidityNum", 0))
    if liquidity < MIN_LIQUIDITY:
        return None

    for outcome, price_str in zip(outcomes, prices):
        price = float(price_str)
        if price < NEAR_CERTAIN_THRESHOLD:
            continue

        end_date = market.get("endDateIso") or market.get("endDate")
        if not end_date:
            continue
        days = days_to_resolution(market["endDate"])

        raw_return = (1 - price) / price  # payout $1 for cost $price
        annualized = (1 + raw_return) ** (365 / days) - 1

        return {
            "question": market["question"],
            "outcome": outcome,
            "price": price,
            "liquidity": liquidity,
            "days_to_resolution": round(days, 2),
            "raw_return_pct": round(raw_return * 100, 3),
            "naive_annualized_pct": round(annualized * 100, 1),
            "slug": market.get("slug"),
        }
    return None


def scan(limit=200):
    markets = get_markets(limit=limit)
    hits = [score_market(m) for m in markets]
    hits = [h for h in hits if h]
    hits.sort(key=lambda h: h["raw_return_pct"], reverse=True)
    return hits


if __name__ == "__main__":
    results = scan()
    print(f"{len(results)} near-certain markets found (price >= {NEAR_CERTAIN_THRESHOLD}, liquidity >= ${MIN_LIQUIDITY})\n")
    for r in results[:20]:
        print(
            f"{r['raw_return_pct']:>6}% raw | {r['naive_annualized_pct']:>8}% naive-annualized | "
            f"{r['days_to_resolution']:>6}d | ${r['liquidity']:>12,.0f} liq | {r['outcome']:>4} | {r['question']}"
        )
