# Polymarket Near-Certainty Scanner (paper trading)

Scans live Polymarket markets for outcomes priced near-certain (>=95%) and
sizes hypothetical positions, so the strategy can be evaluated against
reality before any real capital is involved.

## What this is NOT

On a live pull (2026-06-30), the actual raw edges on near-certain markets ranged ~0.5%-3.4% *per market*, realized over
days to months, not daily. A handful of them are correlated (all "will X win
the World Cup" markets move together on the same tournament outcome), so
they are not independent bets either.

## Setup

```
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```
cd backtest
python3 scanner.py        # print current near-certain markets + naive returns
python3 paper_trader.py   # size + log candidates to paper_trades.csv
```

## Known gaps before this is a real strategy

- `price` is used as the probability estimate in `paper_trader.py` —
  that's circular (you're betting the market is wrong using the market's
  own number). Needs an independent probability model to have real edge.
- No settlement checker yet — `paper_trades.csv` needs a follow-up script
  that checks `closed`/`umaResolutionStatus` on each slug and marks
  win/loss so the model can be scored.
- No correlation/exposure control across related markets (e.g. don't go
  full size on 8 different World Cup winner markets that share risk).
- No transaction cost / slippage modeling from real order book depth yet
  (`gamma_client.get_orderbook` fetches it, but scanner doesn't use it).
