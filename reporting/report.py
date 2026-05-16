"""
Generates:
  1. Rich console metrics table
  2. results/equity_curve.png — equity vs. SPY benchmark + drawdown
  3. results/trades.csv
  4. results/summary.txt
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import yfinance as yf
from rich.console import Console
from rich.table import Table
from rich import box

import config
from backtest.engine import BacktestResult

console = Console()
RESULTS_DIR = Path("results")


def _fetch_benchmark(start: pd.Timestamp, end: pd.Timestamp) -> pd.Series | None:
    try:
        raw = yf.download(
            config.BENCHMARK_TICKER,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        if "Close" not in raw.columns or raw.empty:
            return None
        close = raw["Close"].tz_localize(None) if raw["Close"].index.tz else raw["Close"]
        return close
    except Exception as exc:
        console.print(f"[yellow]Warning: Could not fetch {config.BENCHMARK_TICKER}: {exc}[/yellow]")
        return None


def _normalise(series: pd.Series, base: float = 100_000) -> pd.Series:
    return series / series.iloc[0] * base


def _compute_drawdown(equity: pd.Series) -> pd.Series:
    rolling_max = equity.cummax()
    return (equity - rolling_max) / rolling_max * 100


def generate_report(result: BacktestResult) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    m = result.metrics
    equity = result.equity_curve

    # ── 1. Rich console table ──────────────────────────────────────────────────
    table = Table(
        title="[bold cyan]Backtest Results — Small-Cap Momentum + Mean-Reversion Exit[/bold cyan]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Metric", style="bold", min_width=28)
    table.add_column("Value", justify="right", min_width=14)

    def _fmt(val, suffix="", decimals=2, warn_negative=False):
        formatted = f"{val:.{decimals}f}{suffix}"
        if warn_negative and val < 0:
            return f"[red]{formatted}[/red]"
        if not warn_negative and val > 0 and suffix == "%":
            return f"[green]{formatted}[/green]"
        return formatted

    rows = [
        ("Total Return",           _fmt(m.get("total_return_pct", 0),        "%", warn_negative=True)),
        ("Annualised Return",      _fmt(m.get("annualized_return_pct", 0),   "%", warn_negative=True)),
        ("Max Drawdown",           _fmt(m.get("max_drawdown_pct", 0),        "%", warn_negative=True)),
        ("Sharpe Ratio",           _fmt(m.get("sharpe_ratio", 0),            "",  decimals=3)),
        ("Win Rate",               _fmt(m.get("win_rate_pct", 0),            "%")),
        ("Avg Win",                _fmt(m.get("avg_win_pct", 0),             "%")),
        ("Avg Loss",               _fmt(m.get("avg_loss_pct", 0),            "%", warn_negative=True)),
        ("Profit Factor",          _fmt(m.get("profit_factor", 0),           "",  decimals=3)),
        ("Total Trades",           str(m.get("total_trades", 0))),
        ("Avg Holding Days",       _fmt(m.get("avg_holding_days", 0),        "d", decimals=1)),
    ]

    # Compute alpha vs SPY if possible
    spy = _fetch_benchmark(equity.index[0], equity.index[-1])
    if spy is not None:
        spy_aligned = spy.reindex(equity.index, method="ffill").dropna()
        if len(spy_aligned) > 1:
            spy_return = (spy_aligned.iloc[-1] / spy_aligned.iloc[0] - 1) * 100
            alpha = m.get("total_return_pct", 0) - spy_return
            rows.append(("SPY Return (benchmark)",  _fmt(spy_return, "%", warn_negative=True)))
            rows.append(("Alpha vs SPY",             _fmt(alpha, "%", warn_negative=True)))

    for label, value in rows:
        table.add_row(label, value)

    console.print(table)

    # Warnings
    if m.get("sharpe_ratio", 1) < 0.5:
        console.print("[yellow]⚠ Warning: Sharpe ratio < 0.5 — strategy may not be robust.[/yellow]")
    if abs(m.get("max_drawdown_pct", 0)) > 40:
        console.print("[red]⚠ Warning: Max drawdown > 40% — high risk profile.[/red]")

    # ── 2. Equity curve chart ─────────────────────────────────────────────────
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [3, 1]})
    fig.patch.set_facecolor("#0d1117")
    for ax in axes:
        ax.set_facecolor("#0d1117")
        ax.tick_params(colors="#8b949e")
        for spine in ax.spines.values():
            spine.set_color("#30363d")

    # Top: equity curve
    ax1 = axes[0]
    ax1.plot(equity.index, equity.values, color="#58a6ff", linewidth=1.8, label="Strategy")

    if spy is not None and len(spy_aligned) > 1:
        spy_norm = _normalise(spy_aligned, base=config.INITIAL_CAPITAL)
        ax1.plot(spy_norm.index, spy_norm.values, color="#8b949e", linewidth=1.2,
                 linestyle="--", label=f"{config.BENCHMARK_TICKER} (benchmark)")

    ax1.set_title("Portfolio Equity vs. Benchmark", color="#e6edf3", fontsize=13, pad=12)
    ax1.set_ylabel("Portfolio Value ($)", color="#8b949e")
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax1.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="#e6edf3")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax1.grid(color="#21262d", linewidth=0.5)

    # Bottom: drawdown
    ax2 = axes[1]
    dd = _compute_drawdown(equity)
    ax2.fill_between(dd.index, dd.values, 0, color="#f85149", alpha=0.4)
    ax2.plot(dd.index, dd.values, color="#f85149", linewidth=0.8)
    ax2.set_ylabel("Drawdown (%)", color="#8b949e")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax2.grid(color="#21262d", linewidth=0.5)
    ax2.set_ylim(top=2)

    plt.tight_layout(pad=2)
    chart_path = RESULTS_DIR / "equity_curve.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    plt.close()
    console.print(f"[green]Chart saved → {chart_path}[/green]")

    # ── 3. Trade log CSV ──────────────────────────────────────────────────────
    if not result.trades.empty:
        csv_path = RESULTS_DIR / "trades.csv"
        result.trades.to_csv(csv_path, index=False)
        console.print(f"[green]Trades saved → {csv_path}[/green]")

    # ── 4. Summary text ───────────────────────────────────────────────────────
    lines = ["BACKTEST SUMMARY — Small-Cap Momentum + Mean-Reversion Exit\n"]
    lines.append(f"Period: {equity.index[0].date()} to {equity.index[-1].date()}\n")
    lines.append("-" * 50 + "\n")
    for label, _ in rows:
        key = label.replace(" ", "_").lower().replace("-", "_").replace("(", "").replace(")", "").replace("__", "_")
        # Find metric value
        metric_map = {
            "total_return": m.get("total_return_pct"),
            "annualised_return": m.get("annualized_return_pct"),
            "max_drawdown": m.get("max_drawdown_pct"),
            "sharpe_ratio": m.get("sharpe_ratio"),
            "win_rate": m.get("win_rate_pct"),
            "avg_win": m.get("avg_win_pct"),
            "avg_loss": m.get("avg_loss_pct"),
            "profit_factor": m.get("profit_factor"),
            "total_trades": m.get("total_trades"),
            "avg_holding_days": m.get("avg_holding_days"),
        }
        val = next((v for k, v in metric_map.items() if k in key), None)
        lines.append(f"{label:<28} {val}\n")

    txt_path = RESULTS_DIR / "summary.txt"
    txt_path.write_text("".join(lines), encoding="utf-8")
    console.print(f"[green]Summary saved → {txt_path}[/green]")
