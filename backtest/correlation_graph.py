"""Build a graph of open paper positions grouped by shared underlying event
(e.g. all 'will X win the World Cup' markets share the same event and are
not independent bets). Flags clusters that eat too much of the bankroll at
once, which the flat 5%-per-market cap in paper_trader.py doesn't catch."""
import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, "../data")
from gamma_client import GAMMA_URL  # noqa: E402
import requests  # noqa: E402

LOG_PATH = os.path.join(os.path.dirname(__file__), "paper_trades.csv")
GRAPH_PATH = os.path.join(os.path.dirname(__file__), "..", "correlation_graph.json")
BANKROLL = 10_000.0
CLUSTER_EXPOSURE_WARN_PCT = 0.15  # warn if one event cluster > 15% of bankroll


def get_market_events(slug):
    resp = requests.get(f"{GAMMA_URL}/markets", params={"slug": slug}, timeout=10)
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return []
    return [(e["id"], e.get("ticker") or e.get("slug"), e.get("title")) for e in results[0].get("events", [])]


def build_graph():
    with open(LOG_PATH, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["status"] == "open"]

    clusters = defaultdict(lambda: {"title": None, "positions": [], "exposure": 0.0})
    unclustered = []

    for r in rows:
        events = get_market_events(r["slug"])
        if not events:
            unclustered.append(r)
            continue
        event_id, _, title = events[0]  # a market can span multiple events; use primary
        clusters[event_id]["title"] = title
        clusters[event_id]["exposure"] += float(r["position_size"])
        clusters[event_id]["positions"].append({
            "slug": r["slug"], "question": r["question"],
            "outcome": r["outcome"], "size": float(r["position_size"]),
        })

    graph = {
        "bankroll": BANKROLL,
        "clusters": [
            {
                "event_id": eid,
                "title": c["title"],
                "market_count": len(c["positions"]),
                "total_exposure": round(c["exposure"], 2),
                "pct_of_bankroll": round(100 * c["exposure"] / BANKROLL, 2),
                "over_limit": c["exposure"] / BANKROLL > CLUSTER_EXPOSURE_WARN_PCT,
                "positions": c["positions"],
            }
            for eid, c in clusters.items()
        ],
        "unclustered_count": len(unclustered),
    }
    graph["clusters"].sort(key=lambda c: c["total_exposure"], reverse=True)
    return graph


if __name__ == "__main__":
    graph = build_graph()
    with open(GRAPH_PATH, "w") as f:
        json.dump(graph, f, indent=2)

    print(f"{len(graph['clusters'])} event clusters, {graph['unclustered_count']} standalone positions\n")
    for c in graph["clusters"]:
        flag = " <-- OVER LIMIT" if c["over_limit"] else ""
        print(f"{c['pct_of_bankroll']:>6}% | {c['market_count']} markets | ${c['total_exposure']:>8,.2f} | {c['title']}{flag}")
    print(f"\nWrote graph to {GRAPH_PATH}")
