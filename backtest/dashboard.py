"""Generate a static HTML dashboard from paper_trades.csv: bankroll curve,
win rate, open vs settled positions. Run this after settlement_checker.py."""
import csv
import json
import os

LOG_PATH = os.path.join(os.path.dirname(__file__), "paper_trades.csv")
GRAPH_PATH = os.path.join(os.path.dirname(__file__), "..", "correlation_graph.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "dashboard.html")
STARTING_BANKROLL = 10_000.0


def load_graph():
    if not os.path.exists(GRAPH_PATH):
        return None
    with open(GRAPH_PATH) as f:
        return json.load(f)


def load_rows():
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, newline="") as f:
        return list(csv.DictReader(f))


def build_dashboard(rows):
    settled = [r for r in rows if r["status"] in ("win", "loss")]
    open_rows = [r for r in rows if r["status"] == "open"]

    cumulative = STARTING_BANKROLL
    curve = [{"trade": 0, "bankroll": cumulative}]
    for i, r in enumerate(sorted(settled, key=lambda r: r["logged_at"]), start=1):
        cumulative += float(r["pnl"] or 0)
        curve.append({"trade": i, "bankroll": round(cumulative, 2)})

    wins = sum(1 for r in settled if r["status"] == "win")
    win_rate = round(100 * wins / len(settled), 1) if settled else None
    total_pnl = round(sum(float(r["pnl"] or 0) for r in settled), 2)

    data = {
        "curve": curve,
        "win_rate": win_rate,
        "settled_count": len(settled),
        "open_count": len(open_rows),
        "total_pnl": total_pnl,
        "open_rows": open_rows,
        "settled_rows": settled,
    }
    return data


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Polymarket Paper Trading Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  body {{ font-family: -apple-system, sans-serif; margin: 2rem; background: #0d1117; color: #e6edf3; }}
  h1 {{ font-size: 1.4rem; }}
  .stats {{ display: flex; gap: 2rem; margin: 1.5rem 0; }}
  .stat {{ background: #161b22; padding: 1rem 1.5rem; border-radius: 8px; }}
  .stat .label {{ font-size: 0.75rem; color: #8b949e; text-transform: uppercase; }}
  .stat .value {{ font-size: 1.6rem; font-weight: 600; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; font-size: 0.85rem; }}
  th, td {{ text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #21262d; }}
  th {{ color: #8b949e; }}
  .win {{ color: #3fb950; }}
  .loss {{ color: #f85149; }}
  .open {{ color: #d29922; }}
  canvas {{ background: #161b22; border-radius: 8px; padding: 1rem; }}
</style>
</head>
<body>
<h1>Polymarket Paper Trading Dashboard</h1>
<p style="color:#8b949e">Not real trading yet -- simulated positions only. See README for what's still missing before real capital.</p>

<div class="stats">
  <div class="stat"><div class="label">Bankroll</div><div class="value">${bankroll:,.2f}</div></div>
  <div class="stat"><div class="label">Total PnL</div><div class="value">${total_pnl:,.2f}</div></div>
  <div class="stat"><div class="label">Win Rate</div><div class="value">{win_rate}</div></div>
  <div class="stat"><div class="label">Settled</div><div class="value">{settled_count}</div></div>
  <div class="stat"><div class="label">Open</div><div class="value">{open_count}</div></div>
</div>

<canvas id="curveChart" height="80"></canvas>

<h2>Correlated Exposure (by underlying event)</h2>
<p style="color:#8b949e">Markets on the same event share risk -- these aren't independent bets. Clusters over 15% of bankroll are flagged.</p>
<table>
<tr><th>Event</th><th>Markets</th><th>Total Exposure</th><th>% of Bankroll</th></tr>
{cluster_table_rows}
</table>

<h2>Open Positions</h2>
<table>
<tr><th>Question</th><th>Outcome</th><th>Entry Price</th><th>Days to Resolution</th><th>Position Size</th></tr>
{open_table_rows}
</table>

<h2>Settled Trades</h2>
<table>
<tr><th>Question</th><th>Outcome</th><th>Entry Price</th><th>Status</th><th>PnL</th></tr>
{settled_table_rows}
</table>

<script>
const curve = {curve_json};
new Chart(document.getElementById('curveChart'), {{
  type: 'line',
  data: {{
    labels: curve.map(c => c.trade),
    datasets: [{{
      label: 'Bankroll',
      data: curve.map(c => c.bankroll),
      borderColor: '#58a6ff',
      backgroundColor: 'rgba(88,166,255,0.1)',
      fill: true,
      tension: 0.15,
    }}]
  }},
  options: {{
    scales: {{
      x: {{ title: {{ display: true, text: 'Settled trade #', color: '#8b949e' }}, ticks: {{ color: '#8b949e' }} }},
      y: {{ ticks: {{ color: '#8b949e' }} }}
    }},
    plugins: {{ legend: {{ labels: {{ color: '#e6edf3' }} }} }}
  }}
}});
</script>
</body>
</html>
"""


def row_html(rows, kind):
    out = []
    for r in rows:
        if kind == "open":
            out.append(
                f"<tr><td>{r['question']}</td><td>{r['outcome']}</td>"
                f"<td>{float(r['price']):.3f}</td><td>{r['days_to_resolution']}</td>"
                f"<td>${float(r['position_size']):,.2f}</td></tr>"
            )
        else:
            css = "win" if r["status"] == "win" else "loss"
            out.append(
                f"<tr><td>{r['question']}</td><td>{r['outcome']}</td>"
                f"<td>{float(r['price']):.3f}</td><td class='{css}'>{r['status']}</td>"
                f"<td class='{css}'>${float(r['pnl'] or 0):,.2f}</td></tr>"
            )
    return "\n".join(out) if out else "<tr><td colspan='5'>None yet</td></tr>"


def cluster_table_html(graph):
    if not graph or not graph["clusters"]:
        return "<tr><td colspan='4'>No correlation graph yet -- run correlation_graph.py</td></tr>"
    out = []
    for c in graph["clusters"]:
        css = " class='loss'" if c["over_limit"] else ""
        out.append(
            f"<tr><td{css}>{c['title']}</td><td{css}>{c['market_count']}</td>"
            f"<td{css}>${c['total_exposure']:,.2f}</td><td{css}>{c['pct_of_bankroll']}%"
            f"{' ⚠️' if c['over_limit'] else ''}</td></tr>"
        )
    return "\n".join(out)


def render(data, graph=None):
    bankroll = data["curve"][-1]["bankroll"]
    html = HTML_TEMPLATE.format(
        bankroll=bankroll,
        total_pnl=data["total_pnl"],
        win_rate=f"{data['win_rate']}%" if data["win_rate"] is not None else "n/a",
        settled_count=data["settled_count"],
        open_count=data["open_count"],
        open_table_rows=row_html(data["open_rows"], "open"),
        settled_table_rows=row_html(data["settled_rows"], "settled"),
        cluster_table_rows=cluster_table_html(graph),
        curve_json=json.dumps(data["curve"]),
    )
    with open(OUT_PATH, "w") as f:
        f.write(html)
    print(f"Wrote dashboard to {OUT_PATH}")


if __name__ == "__main__":
    rows = load_rows()
    render(build_dashboard(rows), load_graph())
