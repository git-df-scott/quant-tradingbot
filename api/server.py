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
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

import config

app = FastAPI(title="Quant-Bot V1", docs_url=None, redoc_url=None)

CACHE_FILE = Path("results/backtest_cache.json")
STATIC_DIR = Path(__file__).parent / "static"

_status: dict = {"state": "idle", "msg": ""}


# ── Backtest runner ───────────────────────────────────────────────────────────

def _run_and_cache(start_date: Optional[str] = None, end_date: Optional[str] = None) -> None:
    global _status
    date_label = f"{start_date or 'start'} to {end_date or 'now'}"
    try:
        _status = {"state": "running", "msg": f"Fetching data ({date_label})..."}
        from data.fetch import fetch_all
        price_data = fetch_all()

        # ── Signal generation on FULL history (momentum needs full lookback) ────
        _status["msg"] = f"Generating signals ({date_label})..."
        from signals.momentum import generate_signals
        signals_df = generate_signals(price_data)

        # ── Log actual data coverage ────────────────────────────────────────────
        all_dates = sorted(set(
            d for df in price_data.values() for d in df.index.normalize()
        ))
        data_start = all_dates[0].date() if all_dates else "?"
        data_end   = all_dates[-1].date() if all_dates else "?"
        print(f"[data] coverage: {data_start} to {data_end} ({len(all_dates)} trading days)")

        # ── Trim price_data and signals to the requested window ─────────────────
        pre_window_bars: dict = {}
        if start_date or end_date:
            ts_start = pd.Timestamp(start_date).normalize() if start_date else None
            ts_end   = pd.Timestamp(end_date).normalize()   if end_date   else None

            filtered_prices: dict = {}
            for ticker, df in price_data.items():
                idx = df.index.normalize()
                # Count bars BEFORE the window start — used by engine for 60-bar check
                if ts_start is not None:
                    pre_window_bars[ticker] = int((idx < ts_start).sum())
                else:
                    pre_window_bars[ticker] = 0

                mask = pd.Series(True, index=df.index)
                if ts_start is not None:
                    mask &= idx >= ts_start
                if ts_end is not None:
                    mask &= idx <= ts_end
                d = df[mask.values]
                if len(d) >= 5:
                    filtered_prices[ticker] = d
                    print(f"[data] {ticker}: {len(d)} bars in window "
                          f"(+{pre_window_bars.get(ticker,0)} pre-window bars)")
            price_data = filtered_prices
            print(f"[data] {len(price_data)} tickers have data in the requested window")

            if not signals_df.empty:
                sig_dates = pd.to_datetime(signals_df["date"]).dt.normalize()
                smask = pd.Series(True, index=signals_df.index)
                if ts_start is not None:
                    smask &= sig_dates >= ts_start
                if ts_end is not None:
                    smask &= sig_dates <= ts_end
                signals_df = signals_df[smask.values]
            print(f"[data] {len(signals_df)} signals in window")

        _status["msg"] = f"Computing market regime ({date_label})..."
        from risk.regime import compute_spy_regime
        regime_dates = sorted(set(
            d for df in price_data.values() for d in df.index.normalize()
        ))
        if regime_dates:
            spy_regime = compute_spy_regime(regime_dates[0], regime_dates[-1])
            print(f"[regime] {spy_regime.value_counts().to_dict()}")
        else:
            spy_regime = None

        _status["msg"] = f"Running backtest ({date_label})..."
        from backtest.engine import run as run_engine
        result = run_engine(
            price_data, signals_df,
            pre_window_bars=pre_window_bars or None,
            spy_regime=spy_regime,
        )

        _status["msg"] = "Fetching SPY benchmark..."
        equity = result.equity_curve

        if equity.empty:
            print("[warn] equity curve is empty — no data in requested window")
            _status = {"state": "error", "msg": "No price data in the selected date range. Try a wider window."}
            return

        spy_aligned = pd.Series(dtype=float)
        try:
            # Add one day to end so yfinance includes the last trading day
            spy_end = (equity.index[-1] + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            spy_data = yf.download(
                config.BENCHMARK_TICKER,
                start=equity.index[0].strftime("%Y-%m-%d"),
                end=spy_end,
                auto_adjust=True,
                progress=False,
            )
            if isinstance(spy_data.columns, pd.MultiIndex):
                spy_data.columns = spy_data.columns.get_level_values(0)

            if not spy_data.empty:
                spy_close = spy_data["Close"].copy()
                if hasattr(spy_close.index, "tz") and spy_close.index.tz:
                    spy_close.index = spy_close.index.tz_convert(None)
                spy_norm = spy_close / spy_close.iloc[0] * config.INITIAL_CAPITAL
                spy_aligned = spy_norm.reindex(equity.index, method="ffill").dropna()
            else:
                print(f"[warn] SPY download returned no data for this window")
        except Exception as spy_exc:
            print(f"[warn] SPY fetch failed: {spy_exc}")

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
        _status = {"state": "complete", "msg": f"Done — {date_label}"}

    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        print(f"[error] _run_and_cache failed:\n{tb}")
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
def run(
    start_date: Optional[str] = Query(default=None),
    end_date:   Optional[str] = Query(default=None),
):
    if _status.get("state") == "running":
        return {"status": "already_running"}
    CACHE_FILE.unlink(missing_ok=True)
    t = threading.Thread(
        target=_run_and_cache,
        kwargs={"start_date": start_date, "end_date": end_date},
        daemon=True,
    )
    t.start()
    return {"status": "started", "start_date": start_date, "end_date": end_date}
