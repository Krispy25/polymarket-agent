#!/bin/bash
# Daily pipeline: scan -> log new candidates -> check settlements -> rebuild dashboard -> commit+push.
set -euo pipefail
cd "$(dirname "$0")"
source venv/bin/activate

cd backtest
python3 paper_trader.py
python3 settlement_checker.py
python3 correlation_graph.py
python3 dashboard.py
cd ..

git pull --no-edit -q origin main

git add dashboard.html backtest/paper_trades.csv correlation_graph.json
if ! git diff --cached --quiet; then
  git commit -m "Daily update: $(date -u +%Y-%m-%d)" -q
  git push -q origin main
fi
