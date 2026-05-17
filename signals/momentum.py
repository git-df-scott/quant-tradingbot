"""
Cross-sectional momentum signal generation.

ENTRY conditions (all three must be true — V1 logic):
  1. 20-day return in top 30% of universe (momentum-qualified)
  2. Close ≤ 5-day MA  (pullback entry)
  3. Volume > 1.2× 20-day average volume (volume confirmation)

Each signal row includes atr_abs (20-day ATR in dollars) so the engine
can compute a per-trade adaptive stop at fill time.

No look-ahead bias: all computations use only data available at bar t.
Signals generated at close of t; engine fills at open of t+1.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table

import config

console = Console()


def _build_wide_frames(
    price_data: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Stack per-ticker DataFrames into (close, open, volume, high, low) wide frames."""
    closes, opens, volumes, highs, lows = {}, {}, {}, {}, {}
    for ticker, df in price_data.items():
        closes[ticker]  = df["Close"]
        opens[ticker]   = df["Open"]
        volumes[ticker] = df["Volume"]
        highs[ticker]   = df["High"]
        lows[ticker]    = df["Low"]

    close_df  = pd.DataFrame(closes).sort_index()
    open_df   = pd.DataFrame(opens).sort_index()
    volume_df = pd.DataFrame(volumes).sort_index()
    high_df   = pd.DataFrame(highs).sort_index()
    low_df    = pd.DataFrame(lows).sort_index()

    idx = close_df.index.intersection(open_df.index).intersection(volume_df.index)
    return close_df.loc[idx], open_df.loc[idx], volume_df.loc[idx], high_df.loc[idx], low_df.loc[idx]


def generate_signals(price_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Compute entry signals for every (date, ticker) combination.

    Returns DataFrame with columns:
        date, ticker, signal, momentum_rank, pct_from_5ma, volume_ratio,
        momentum_20d, ma5, ma20, close, volume
    """
    close_df, _, volume_df, high_df, low_df = _build_wide_frames(price_data)

    # ── Feature computation (all rolling, no look-ahead) ─────────────────────

    # 20-day return
    mom_20 = close_df.pct_change(config.MOMENTUM_WINDOW)

    # 5-day MA for pullback entry
    ma5 = close_df.rolling(config.ENTRY_MA_WINDOW, min_periods=config.ENTRY_MA_WINDOW).mean()

    # 20-day MA for take-profit target
    ma20 = close_df.rolling(config.EXIT_MA_WINDOW, min_periods=config.EXIT_MA_WINDOW).mean()

    # 20-day average volume
    avg_vol_20 = volume_df.rolling(config.MOMENTUM_WINDOW, min_periods=config.MOMENTUM_WINDOW).mean()

    # 20-day ATR as fraction of price (True Range = max of H-L, |H-prevC|, |prevC-L|)
    prev_close = close_df.shift(1)
    tr = np.maximum(
        np.maximum(
            (high_df - low_df).values,
            (high_df - prev_close).abs().values,
        ),
        (prev_close - low_df).abs().values,
    )
    tr_df  = pd.DataFrame(tr, index=close_df.index, columns=close_df.columns)
    atr_20 = tr_df.rolling(config.MOMENTUM_WINDOW, min_periods=config.MOMENTUM_WINDOW).mean()
    atr_pct = atr_20 / close_df                                        # ATR as fraction of price

    # ── Cross-sectional ranking (per date) ────────────────────────────────────
    mom_rank = mom_20.rank(axis=1, pct=True)

    # ── Conditions (V1) ──────────────────────────────────────────────────────
    cond_momentum = mom_rank >= config.MOMENTUM_PERCENTILE             # top 30%
    cond_pullback = close_df <= ma5                                    # at or below 5-day MA
    cond_volume   = volume_df >= avg_vol_20 * config.VOLUME_MULTIPLIER

    signal_matrix = (cond_momentum & cond_pullback & cond_volume).astype(int)

    # ── Melt to long format ───────────────────────────────────────────────────
    records = []
    tickers = list(price_data.keys())

    for date in signal_matrix.index:
        for ticker in tickers:
            try:
                sig          = signal_matrix.loc[date, ticker]
                mom_val      = mom_20.loc[date, ticker]
                rank_val     = mom_rank.loc[date, ticker]
                ma5_val      = ma5.loc[date, ticker]
                ma20_val     = ma20.loc[date, ticker]
                close_val    = close_df.loc[date, ticker]
                vol_val      = volume_df.loc[date, ticker]
                avg_vol      = avg_vol_20.loc[date, ticker]
                atr_val      = atr_20.loc[date, ticker]       # dollar ATR for adaptive stop
                vol_ratio    = vol_val / avg_vol if avg_vol > 0 else np.nan
                pct_from_ma5 = (close_val - ma5_val) / ma5_val if ma5_val > 0 else np.nan
            except (KeyError, ZeroDivisionError):
                continue

            if any(pd.isna([sig, mom_val, rank_val, ma5_val, close_val])):
                continue

            records.append({
                "date":           date,
                "ticker":         ticker,
                "signal":         int(sig),
                "momentum_rank":  round(rank_val, 4),
                "momentum_20d":   round(mom_val, 4),
                "pct_from_5ma":   round(pct_from_ma5, 4) if not pd.isna(pct_from_ma5) else None,
                "volume_ratio":   round(vol_ratio, 4) if not pd.isna(vol_ratio) else None,
                "atr_abs":        round(atr_val, 4) if not pd.isna(atr_val) else None,
                "ma5":            round(ma5_val, 4),
                "ma20":           round(ma20_val, 4) if not pd.isna(ma20_val) else None,
                "close":          round(close_val, 4),
                "volume":         int(vol_val) if not pd.isna(vol_val) else None,
            })

    df = pd.DataFrame(records)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["date", "momentum_rank"], ascending=[True, False]).reset_index(drop=True)
    return df


def signal_summary(signals_df: pd.DataFrame) -> None:
    """Print signal statistics to console."""
    if signals_df.empty:
        console.print("[red]No signals generated.[/red]")
        return

    fired = signals_df[signals_df["signal"] == 1]
    daily_counts = fired.groupby("date").size()

    console.print("\n[bold cyan]-- Signal Summary -----------------------------------------------[/bold cyan]")
    console.print(f"  Date range : {signals_df['date'].min().date()} to {signals_df['date'].max().date()}")
    console.print(f"  Total bars : {signals_df['date'].nunique()}")
    console.print(f"  Total fires: {len(fired)}")
    console.print(f"  Avg signals/day: {daily_counts.mean():.2f}  (max {daily_counts.max()}, min {daily_counts.min()})")

    # Top firing tickers
    ticker_counts = fired["ticker"].value_counts().head(10)
    table = Table(title="Top Signal Tickers", show_header=True, header_style="bold")
    table.add_column("Ticker")
    table.add_column("Fires", justify="right")
    for ticker, count in ticker_counts.items():
        table.add_row(ticker, str(count))
    console.print(table)

    # Frequency histogram (ASCII)
    console.print("\n[bold]Signals-per-day distribution:[/bold]")
    for n in range(int(daily_counts.max()) + 1):
        count = (daily_counts == n).sum()
        bar = "#" * min(count, 50)
        console.print(f"  {n:2d} signal(s): {bar} {count}")
