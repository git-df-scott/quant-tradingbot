# Agent Instructions

## Package Manager
Use **pip**: `pip install -r requirements.txt`

## Run Commands
| Command | Description |
|---------|-------------|
| `python main.py --mode backtest` | Full 2-year backtest + report |
| `python main.py --mode simulate` | 30-day in-memory market replay |
| `python main.py --mode paper` | Live paper trading (Alpaca) |
| `pytest tests/ -v --tb=short` | Run test suite |

## File-Scoped Validation
```bash
python -c "from data.fetch import fetch_all; print('fetch OK')"
python -c "from signals.momentum import generate_signals; print('signals OK')"
python -c "from backtest.engine import run; print('engine OK')"
```

## Key Invariants
- All parameters in `config.py` — never hardcode values elsewhere
- Signals at close of bar t → fills at open of bar t+1 (no look-ahead)
- `risk/manager.py` is authoritative for sizing — never bypass it
- Cache lives in `data/cache/` — gitignored, TTL 24h

## Env Vars
Copy `.env` and fill in keys for Alpaca. Leaving blank auto-falls back to simulator.

## Commit Attribution
AI commits MUST include:
```
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

## Output Files
| File | Description |
|------|-------------|
| `results/equity_curve.png` | Equity vs SPY + drawdown chart |
| `results/trades.csv` | Full trade log |
| `results/summary.txt` | Plain text metrics |
| `logs/paper_YYYYMMDD.log` | Paper trading activity |
