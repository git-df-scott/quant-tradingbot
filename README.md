---
title: Quant Bot V1
emoji: 📈
colorFrom: cyan
colorTo: blue
sdk: docker
pinned: true
app_port: 7860
---

# Quant-Bot V1 — Small-Cap Momentum + Mean-Reversion Exit

An end-to-end quantitative trading system with live backtesting dashboard.

## Strategy

| Parameter | Value |
|-----------|-------|
| Universe | 25 small-cap stocks, 5 sectors, $50M–$500M market cap (2022) |
| Entry | 20-day return top 30% AND close ≤ 5-day MA AND volume > 1.2× avg |
| Exit | Close crosses above 20-day MA (take profit) OR −8% (stop loss) |
| Sizing | Equal weight, max 10 positions, 10% per slot |
| Capital | $100,000 paper |
| Lookback | 2 years of daily OHLCV data |

## Dashboard

The web app shows:
- Real-time backtest metrics (Sharpe, drawdown, win rate, profit factor)
- Equity curve vs SPY benchmark
- Drawdown panel
- Win/loss donut chart
- Trades-by-ticker bar chart
- Full trade log with pagination

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run dashboard (backtests on startup)
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

# Or run CLI backtest
python main.py --mode backtest
python main.py --mode simulate
python main.py --mode paper
```

## Project Structure

```
config.py           All tunable parameters
data/               Universe, data fetching, caching (yfinance)
signals/            Cross-sectional momentum signal generation
backtest/           Bar-by-bar simulation engine (no lookahead bias)
risk/               Position sizing and stop-loss logic
simulation/         API-free historical market replay
execution/          Alpaca paper trading integration
reporting/          Matplotlib charts + Rich metrics table
api/                FastAPI server + Antigravity dashboard UI
```

## Key Invariants

- Signals generated at bar t close; fills at bar t+1 open — no lookahead bias
- All parameters in `config.py` — never hardcoded elsewhere
- Paper trader auto-falls back to simulator when no API keys are set
- Cache TTL: 24 hours (`data/cache/`)

## Environment Variables (optional)

```
ALPACA_API_KEY=      # Leave blank to use simulator
ALPACA_SECRET_KEY=
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```
