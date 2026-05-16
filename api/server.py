"""
FastAPI server — serves the dashboard and JSON API.
Runs the backtest on startup (background thread) and caches results as JSON.
"""

import json
import threading
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

import config

app = FastAPI(title="Quant-Bot V1", docs_url=None, redoc_url=None)

CACHE_FILE = Path("results/backtest_cache.json")
STATIC_DIR = Path(__file__).parent / "static"

_status: dict = {"state": "idle", "msg": ""}


class RunRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None


# ── Backtest runner ───────────────────────────────────────────────────────────

def _run_and_cache(start_date: Optional[str] = None, end_date: Optional[str] = None) -> None:
    global _status
    try:
        _status = {"state": "running", "msg": "Fetching market data..."}
        from data.fetch import fetch_all
        price_data = fetch_all()

        # Generate signals on the FULL history so momentum has its full lookback.
        # Filtering before this would give NaN signals for the first MOMENTUM_WINDOW bars.
        _status["msg"] = "Generating signals..."
        from signals.momentum import generate_signals
        signals_df = generate_signals(price_data)

        # Now trim both price_data and signals to the requested window.
        if start_date or end_date:
            ts_start = pd.Timestamp(start_date) if start_date else None
            ts_end   = pd.Timestamp(end_date)   if end_date   else None

            filtered = {}
            for ticker, df in price_data.items():
                d = df.copy()
                if ts_start is not None:
                    d = d[d.index >= ts_start]
                if ts_end is not None:
                    d = d[d.index <= ts_end]
                if len(d) > 30:
                    filtered[ticker] = d
            price_data = filtered

            if not signals_df.empty:
                dates = pd.to_datetime(signals_df["date"])
                mask  = pd.Series(True, index=signals_df.index)
                if ts_start is not None:
                    mask &= dates >= ts_start
                if ts_end is not None:
                    mask &= dates <= ts_end
                signals_df = signals_df[mask]

        _status["msg"] = "Running backtest engine..."
        from backtest.engine import run as run_engine
        result = run_engine(price_data, signals_df)

        _status["msg"] = "Fetching SPY benchmark..."
        equity = result.equity_curve

        spy_data = yf.download(
            config.BENCHMARK_TICKER,
            start=equity.index[0].strftime("%Y-%m-%d"),
            end=equity.index[-1].strftime("%Y-%m-%d"),
            auto_adjust=True,
            progress=False,
        )
        if isinstance(spy_data.columns, pd.MultiIndex):
            spy_data.columns = spy_data.columns.get_level_values(0)

        spy_close = spy_data["Close"].copy()
        if hasattr(spy_close.index, "tz") and spy_close.index.tz:
            spy_close.index = spy_close.index.tz_convert(None)
        spy_norm = spy_close / spy_close.iloc[0] * config.INITIAL_CAPITAL

        spy_aligned = spy_norm.reindex(equity.index, method="ffill").dropna()

        def _series_to_list(s: pd.Series) -> list[dict]:
            return [
                {"date": d.strftime("%Y-%m-%d"), "value": round(float(v), 2)}
                for d, v in zip(s.index, s.values)
                if not pd.isna(v)
            ]

        trades_list = []
        if not result.trades.empty:
            for _, row in result.trades.iterrows():
                trades_list.append({
                    "ticker":       str(row.get("ticker", "")),
                    "entry_date":   str(row.get("entry_date", ""))[:10],
                    "exit_date":    str(row.get("exit_date", ""))[:10],
                    "entry_price":  round(float(row.get("entry_price", 0)), 2),
                    "exit_price":   round(float(row.get("exit_price", 0)), 2),
                    "pnl_pct":      round(float(row.get("pnl_pct", 0)) * 100, 3),
                    "pnl_dollar":   round(float(row.get("pnl_dollar", 0)), 2),
                    "holding_days": int(row.get("holding_days", 0)),
                    "exit_reason":  str(row.get("exit_reason", "")),
                })

        signal_stats = {}
        if not result.trades.empty:
            for ticker, cnt in result.trades["ticker"].value_counts().items():
                signal_stats[str(ticker)] = int(cnt)

        # Trade analytics
        _status["msg"] = "Computing trade analytics..."
        from reporting.analysis import analyze_trades, print_analysis
        analysis = analyze_trades(result.trades) if not result.trades.empty else {}
        print_analysis(analysis)

        cache = {
            "metrics":        result.metrics,
            "equity_curve":   _series_to_list(equity),
            "spy_curve":      _series_to_list(spy_aligned),
            "trades":         trades_list,
            "period": {
                "start":        equity.index[0].strftime("%Y-%m-%d"),
                "end":          equity.index[-1].strftime("%Y-%m-%d"),
                "trading_days": len(equity),
            },
            "signal_stats":   signal_stats,
            "universe_size":  config.UNIVERSE_SIZE,
            "initial_capital": config.INITIAL_CAPITAL,
            "analysis":       analysis,
            "date_range":     {"start": start_date, "end": end_date},
        }

        Path("results").mkdir(exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache, default=str), encoding="utf-8")
        _status = {"state": "complete", "msg": "Ready"}

    except Exception as exc:
        _status = {"state": "error", "msg": str(exc)}


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup() -> None:
    if not CACHE_FILE.exists():
        t = threading.Thread(target=_run_and_cache, daemon=True)
        t.start()
    else:
        global _status
        _status = {"state": "complete", "msg": "Loaded from cache"}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    html_file = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/status")
def status():
    return _status


@app.get("/api/results")
def results():
    if not CACHE_FILE.exists():
        return JSONResponse(
            {"error": "backtest_pending", "status": _status},
            status_code=202,
        )
    return JSONResponse(json.loads(CACHE_FILE.read_text(encoding="utf-8")))


@app.post("/api/run")
def run(req: RunRequest = RunRequest()):
    if _status.get("state") == "running":
        return {"status": "already_running"}
    CACHE_FILE.unlink(missing_ok=True)
    t = threading.Thread(
        target=_run_and_cache,
        kwargs={"start_date": req.start_date, "end_date": req.end_date},
        daemon=True,
    )
    t.start()
    return {"status": "started"}
