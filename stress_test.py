"""
Stress test: run backtests for 2022, 2023, 2024 and print comparison table.
Usage: python stress_test.py
"""

from __future__ import annotations

import sys
from datetime import datetime as _dt

import pandas as pd
import yfinance as yf

import config


def run_year(start_date: str, end_date: str) -> dict:
    from data.fetch import fetch_all
    from signals.momentum import generate_signals
    from backtest.engine import run as run_engine
    from risk.regime import compute_spy_regime

    label = f"{start_date[:4]}"
    print(f"\n{'='*60}")
    print(f"  BACKTEST: {start_date} to {end_date}")
    print(f"{'='*60}")

    days_to_window = (_dt.today() - pd.Timestamp(start_date).to_pydatetime()).days
    lookback = max(config.LOOKBACK_DAYS, days_to_window + 200)
    min_start = (pd.Timestamp(start_date) - pd.Timedelta(days=200)).strftime("%Y-%m-%d")

    print(f"  Fetching data (lookback={lookback}d, min_start={min_start})...")
    price_data = fetch_all(lookback_days=lookback, min_start_date=min_start)
    if not price_data:
        print("  No data. Skipping.")
        return {"label": label, "error": "no_data"}

    print(f"  Generating signals across {len(price_data)} tickers...")
    signals_df = generate_signals(price_data)

    ts_start = pd.Timestamp(start_date).normalize()
    ts_end   = pd.Timestamp(end_date).normalize()
    pre_window_bars: dict = {}
    filtered_prices: dict = {}
    for ticker, df in price_data.items():
        idx = df.index.normalize()
        pre_window_bars[ticker] = int((idx < ts_start).sum())
        mask = (idx >= ts_start) & (idx <= ts_end)
        d = df[mask]
        if len(d) >= 5:
            filtered_prices[ticker] = d
    price_data = filtered_prices
    print(f"  {len(price_data)} tickers in window")

    if not signals_df.empty:
        sig_dates = pd.to_datetime(signals_df["date"]).dt.normalize()
        signals_df = signals_df[(sig_dates >= ts_start) & (sig_dates <= ts_end)]
    print(f"  {len(signals_df)} signals in window")

    regime_dates = sorted(set(d for df in price_data.values() for d in df.index.normalize()))
    spy_regime = compute_spy_regime(regime_dates[0], regime_dates[-1]) if regime_dates else None
    if spy_regime is not None and not spy_regime.empty:
        print(f"  Regime: {spy_regime.value_counts().to_dict()}")

    result = run_engine(
        price_data, signals_df,
        pre_window_bars=pre_window_bars or None,
        spy_regime=spy_regime,
    )

    equity = result.equity_curve
    if equity.empty:
        return {"label": label, "error": "empty_equity"}

    spy_return = None
    try:
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
            spy_return = float((spy_close.iloc[-1] / spy_close.iloc[0]) - 1) * 100
    except Exception:
        pass

    m = result.metrics
    alpha = None
    if spy_return is not None and m.get("total_return_pct") is not None:
        alpha = round(m["total_return_pct"] - spy_return, 2)

    return {
        "label": label,
        "total_return":   m.get("total_return_pct"),
        "sharpe":         m.get("sharpe_ratio"),
        "win_rate":       m.get("win_rate_pct"),
        "profit_factor":  m.get("profit_factor"),
        "max_drawdown":   m.get("max_drawdown_pct"),
        "alpha_vs_spy":   alpha,
        "spy_return":     round(spy_return, 2) if spy_return is not None else None,
        "trade_count":    m.get("total_trades", 0),
    }


WINDOWS = [
    ("2022-01-01", "2022-12-31"),
    ("2023-01-01", "2023-12-31"),
    ("2024-01-01", "2024-12-31"),
]


def fmt(v, suffix="", decimals=2):
    if v is None:
        return "—"
    sign = "+" if isinstance(v, float) and v > 0 else ""
    return f"{sign}{v:.{decimals}f}{suffix}"


def main():
    results = []
    for start, end in WINDOWS:
        r = run_year(start, end)
        results.append(r)

    print("\n")
    print("=" * 100)
    print("  STRESS TEST COMPARISON TABLE")
    print("=" * 100)

    col_w = 14
    headers = ["Period", "Total Ret", "SPY Ret", "Alpha", "Sharpe", "Win Rate", "Prof.Factor", "Max DD", "Trades"]
    print("  " + "".join(h.ljust(col_w) for h in headers))
    print("  " + "-" * (col_w * len(headers)))

    for r in results:
        if "error" in r:
            print(f"  {r['label']:<{col_w}}ERROR: {r['error']}")
            continue
        row = [
            r["label"],
            fmt(r.get("total_return"),  "%"),
            fmt(r.get("spy_return"),    "%"),
            fmt(r.get("alpha_vs_spy"),  "pp"),
            fmt(r.get("sharpe"),        "", 3),
            fmt(r.get("win_rate"),      "%"),
            fmt(r.get("profit_factor"), "", 3),
            fmt(r.get("max_drawdown"),  "%"),
            str(r.get("trade_count", 0)),
        ]
        print("  " + "".join(str(c).ljust(col_w) for c in row))

    print("=" * 100)


if __name__ == "__main__":
    main()
