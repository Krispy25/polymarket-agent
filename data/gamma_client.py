"""Thin client for Polymarket's public Gamma API (no auth required)."""
import requests

GAMMA_URL = "https://gamma-api.polymarket.com"


def get_markets(limit=100, active=True, closed=False, order="volume24hr", ascending=False):
    params = {
        "limit": limit,
        "active": str(active).lower(),
        "closed": str(closed).lower(),
        "order": order,
        "ascending": str(ascending).lower(),
    }
    resp = requests.get(f"{GAMMA_URL}/markets", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_orderbook(token_id):
    """CLOB order book for a specific outcome token."""
    resp = requests.get(
        "https://clob.polymarket.com/book",
        params={"token_id": token_id},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
