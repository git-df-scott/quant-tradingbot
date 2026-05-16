# Quant-Bot V1 — Small-Cap Momentum + Mean-Reversion Exit

## Strategy

- **Universe**: 25 small-cap stocks ($50M–$500M market cap, 2022), 5 sectors
- **Entry**: 20-day return in top 30% AND close ≤ 5-day MA AND volume > 1.2× avg
- **Exit**: Close crosses above 20-day MA (take profit) OR −8% from entry (stop)
- **Sizing**: Equal weight, max 10 open positions, 10% per slot
- **Capital**: $100,000 paper

## Quick Start

```bash
pip install -r requirements.txt
python main.py --mode backtest
```

## Modes

| Mode | Command | Description |
|------|---------|-------------|
| Backtest | `python main.py --mode backtest` | 2-year historical backtest |
| Simulate | `python main.py --mode simulate` | 30-day market replay (no API) |
| Paper | `python main.py --mode paper` | Live Alpaca paper trading |

## Structure

```
config.py          All tunable parameters
data/              Universe, data fetching, caching
signals/           Cross-sectional momentum signal logic
backtest/          Bar-by-bar simulation engine
risk/              Position sizing and stop logic
simulation/        API-free historical replay
execution/         Alpaca paper trading wrapper
reporting/         Charts, trade log, metrics table
```

## Outputs

- `results/equity_curve.png` — Equity vs SPY benchmark + drawdown panel
- `results/trades.csv` — Full trade log with entry/exit/P&L
- `results/summary.txt` — Plain text metrics dump

## Configuration

All parameters are in `config.py`. Never hardcode values elsewhere.
