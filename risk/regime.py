"""
Market regime detection based on SPY SMA50 / SMA200.

Labels (assigned at bar close, applied at next open):
  bull    — SPY >= SMA200 AND SMA50 >= SMA200  (normal operation)
  caution — SPY <  SMA200 but SMA50 >= SMA200  (halved size/slots)
  bear    — SMA50 < SMA200 (death cross active) (no new entries)

NaN periods (before SMA warmup) default to "bull".
"""
from __future__ import annotations

from datetime import timedelta

import pandas as pd
import yfinance as yf

import config


def compute_spy_regime(
    start: pd.Timestamp | str,
    end:   pd.Timestamp | str,
    fast: int = config.REGIME_SMA_FAST,
    slow: int = config.REGIME_SMA_SLOW,
) -> pd.Series:
    """
    Fetches SPY from (start - 2×slow) to end+1 to warm up both SMAs,
    then returns a Series[str] indexed by normalized date covering start..end.
    Returns an empty Series on any failure; engine falls back to 'bull'.
    """
    fetch_start = (pd.Timestamp(start) - timedelta(days=slow * 2)).strftime("%Y-%m-%d")
    fetch_end   = (pd.Timestamp(end)   + timedelta(days=2)).strftime("%Y-%m-%d")

    try:
        raw = yf.download(
            "SPY", start=fetch_start, end=fetch_end,
            auto_adjust=True, progress=False, threads=False,
        )
        if raw.empty:
            return pd.Series(dtype=str, name="regime")
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        close = raw["Close"].copy()
        if hasattr(close.index, "tz") and close.index.tz:
            close.index = close.index.tz_convert(None)
        close.index = close.index.normalize()

        sma_fast = close.rolling(fast, min_periods=fast).mean()
        sma_slow = close.rolling(slow, min_periods=slow).mean()

        regime = pd.Series("bull", index=close.index, dtype=str, name="regime")
        regime[close < sma_slow]                                       = "caution"
        regime[sma_fast.notna() & sma_slow.notna() & (sma_fast < sma_slow)] = "bear"
        regime[sma_slow.isna()]                                        = "bull"

        ts_start = pd.Timestamp(start).normalize()
        ts_end   = pd.Timestamp(end).normalize()
        return regime[(regime.index >= ts_start) & (regime.index <= ts_end)]

    except Exception as exc:
        print(f"[regime] SPY regime fetch failed: {exc}")
        return pd.Series(dtype=str, name="regime")
