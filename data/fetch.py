"""
Downloads and caches OHLCV daily data via yfinance.
Cache TTL = 24 hours. Returns dict {ticker: DataFrame}.
"""

import os
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf
from rich.console import Console
from rich.table import Table

import config
from data.universe import TICKERS

warnings.filterwarnings("ignore", category=FutureWarning)

console = Console()

CACHE_DIR = Path(config.DATA_CACHE_DIR)
REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]
MIN_TRADING_DAYS = 100


def _cache_path(ticker: str) -> Path:
    return CACHE_DIR / f"{ticker}.csv"


def _is_cache_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(hours=config.CACHE_TTL_HOURS)


def _load_from_cache(ticker: str) -> pd.DataFrame | None:
    path = _cache_path(ticker)
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
        return df
    except Exception:
        return None


def _save_to_cache(ticker: str, df: pd.DataFrame) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(_cache_path(ticker))


def _download_ticker(ticker: str, start: str, end: str) -> tuple[pd.DataFrame | None, str]:
    """Returns (df, warning_msg). df is None on failure. Tries Ticker.history() first."""
    # Primary: yf.Ticker.history() — more robust for individual tickers
    try:
        t = yf.Ticker(ticker)
        raw = t.history(start=start, end=end, interval="1d", auto_adjust=True, actions=False)

        if raw is None or raw.empty:
            raise ValueError("empty result from Ticker.history()")

        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        available = [c for c in REQUIRED_COLUMNS if c in raw.columns]
        if len(available) < len(REQUIRED_COLUMNS):
            raise ValueError(f"missing columns: {set(REQUIRED_COLUMNS) - set(available)}")

        df = raw[available].copy()

        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_convert(None)

        df.index = pd.to_datetime(df.index).normalize()
        df = df.dropna(subset=["Close"])
        df["AdjClose"] = df["Close"]

        if len(df) < MIN_TRADING_DAYS:
            return None, f"only {len(df)} trading days (min {MIN_TRADING_DAYS})"

        return df, ""

    except Exception as exc1:
        # Fallback: yf.download()
        try:
            raw = yf.download(
                ticker, start=start, end=end, interval="1d",
                auto_adjust=True, progress=False, threads=False,
            )
            if raw.empty:
                return None, f"no data: {exc1}"

            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)

            raw = raw.rename(columns={"Adj Close": "AdjClose"})
            available = [c for c in REQUIRED_COLUMNS if c in raw.columns]
            if len(available) < len(REQUIRED_COLUMNS):
                return None, f"missing cols after fallback"

            df = raw[available].copy()
            if hasattr(df.index, "tz") and df.index.tz is not None:
                df.index = df.index.tz_convert(None)
            df.index = pd.to_datetime(df.index).normalize()
            df = df.dropna(subset=["Close"])
            df["AdjClose"] = df["Close"]

            if len(df) < MIN_TRADING_DAYS:
                return None, f"only {len(df)} rows"

            return df, ""

        except Exception as exc2:
            return None, str(exc2)


def fetch_all(
    tickers: list[str] = TICKERS,
    lookback_days: int = config.LOOKBACK_DAYS,
    force_refresh: bool = False,
    min_start_date: str | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Download OHLCV for all tickers. Returns only tickers with clean data.
    Caches to CSV; skips download if cache is fresh (<24h) unless force_refresh.

    min_start_date: if set, cached data whose first bar is after this date is
    treated as stale and re-downloaded, ensuring enough pre-window history for
    historical backtests.
    """
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    result: dict[str, pd.DataFrame] = {}
    summary_rows: list[dict] = []

    for ticker in tickers:
        path = _cache_path(ticker)
        warning = ""

        use_cache = not force_refresh and _is_cache_fresh(path)
        if use_cache and min_start_date:
            cached_peek = _load_from_cache(ticker)
            if cached_peek is None or cached_peek.empty:
                use_cache = False
            elif cached_peek.index[0].normalize() > pd.Timestamp(min_start_date):
                use_cache = False

        if use_cache:
            df = _load_from_cache(ticker)
            source = "cache"
            if df is None:
                warning = "cache read failed"
        else:
            df, warning = _download_ticker(ticker, start_date, end_date)
            source = "download"
            if df is not None:
                _save_to_cache(ticker, df)

        if df is not None and len(df) >= MIN_TRADING_DAYS:
            result[ticker] = df
            date_range = f"{df.index[0].date()} to {df.index[-1].date()}"
            summary_rows.append({
                "ticker": ticker,
                "rows": str(len(df)),
                "date_range": date_range,
                "source": source,
                "warning": warning or "OK",
            })
        else:
            summary_rows.append({
                "ticker": ticker,
                "rows": "—",
                "date_range": "—",
                "source": source,
                "warning": f"SKIPPED: {warning}",
            })

    _print_summary(summary_rows)
    console.print(f"\n[bold green]Loaded {len(result)}/{len(tickers)} tickers successfully.[/bold green]\n")
    return result


def _print_summary(rows: list[dict]) -> None:
    table = Table(title="Data Download Summary", show_header=True, header_style="bold cyan")
    table.add_column("Ticker", style="bold")
    table.add_column("Rows", justify="right")
    table.add_column("Date Range")
    table.add_column("Source")
    table.add_column("Status")

    for r in rows:
        status_style = "red" if r["warning"].startswith("SKIPPED") else "green"
        table.add_row(
            r["ticker"],
            r["rows"],
            r["date_range"],
            r["source"],
            f"[{status_style}]{r['warning']}[/{status_style}]",
        )

    console.print(table)
