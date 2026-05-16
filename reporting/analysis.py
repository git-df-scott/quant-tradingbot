"""
Trade analytics: win/loss ratio, loss distribution, worst tickers, quarterly breakdown.
Returns structured data for the API and prints Rich summary tables to the console.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

_console = Console()


def analyze_trades(trades_df: pd.DataFrame) -> dict:
    """Compute full trade analytics from a closed-trades DataFrame."""
    if trades_df.empty:
        return {}

    pnl    = trades_df["pnl_pct"]
    wins   = trades_df[pnl > 0]
    losses = trades_df[pnl <= 0]

    avg_win  = float(wins["pnl_pct"].mean()   * 100) if len(wins)   else 0.0
    avg_loss = float(losses["pnl_pct"].mean() * 100) if len(losses) else 0.0
    wl_ratio = abs(avg_win / avg_loss) if avg_loss else None  # None → null (no losses)

    # Loss distribution (all values are percentages)
    loss_dist: dict = {}
    if len(losses):
        lp = losses["pnl_pct"] * 100
        loss_dist = {
            "worst":  round(float(lp.min()),              2),
            "p10":    round(float(lp.quantile(0.10)),     2),
            "p25":    round(float(lp.quantile(0.25)),     2),
            "median": round(float(lp.median()),           2),
            "p75":    round(float(lp.quantile(0.75)),     2),
        }

    # Outliers: losses more than 2σ below mean
    outlier_count, outlier_impact = 0, 0.0
    if len(losses) > 3:
        lp = losses["pnl_pct"] * 100
        mu, sigma = lp.mean(), lp.std()
        mask = lp < mu - 2 * sigma
        outlier_count  = int(mask.sum())
        outlier_impact = round(float(lp[mask].sum()), 2)

    # Worst tickers by avg loss
    worst_tickers: list[dict] = []
    if len(losses):
        grp = (
            losses.groupby("ticker")["pnl_pct"]
            .agg(avg_loss_pct="mean", count="count")
            .reset_index()
        )
        grp["avg_loss_pct"] = (grp["avg_loss_pct"] * 100).round(2)
        grp = grp.sort_values("avg_loss_pct").head(5)
        worst_tickers = grp.to_dict("records")

    # Quarterly breakdown: loss rate and avg PnL per quarter
    quarterly: list[dict] = []
    if len(trades_df) and "exit_date" in trades_df.columns:
        df = trades_df.copy()
        df["exit_date"] = pd.to_datetime(df["exit_date"])
        df["quarter"]   = df["exit_date"].dt.to_period("Q").astype(str)
        for q, grp in df.groupby("quarter"):
            quarterly.append({
                "quarter":   str(q),
                "total":     int(len(grp)),
                "losses":    int((grp["pnl_pct"] <= 0).sum()),
                "loss_rate": round(float((grp["pnl_pct"] <= 0).mean() * 100), 1),
                "avg_pnl":   round(float(grp["pnl_pct"].mean() * 100), 2),
            })

    return {
        "avg_win_pct":        round(avg_win,  2),
        "avg_loss_pct":       round(avg_loss, 2),
        "win_loss_ratio":     round(wl_ratio, 3) if wl_ratio is not None else None,
        "n_wins":             int(len(wins)),
        "n_losses":           int(len(losses)),
        "loss_distribution":  loss_dist,
        "outlier_count":      outlier_count,
        "outlier_impact_pct": outlier_impact,
        "worst_tickers":      worst_tickers,
        "quarterly":          quarterly,
    }


def print_analysis(a: dict) -> None:
    if not a:
        return

    # ── Win / Loss summary ────────────────────────────────────────────────────
    t = Table(title="Win / Loss Summary", header_style="bold cyan", style="dim")
    t.add_column("Metric",  min_width=26)
    t.add_column("Value",   justify="right")
    t.add_row("Avg Win",          f"[green]+{a['avg_win_pct']:.2f}%[/green]")
    t.add_row("Avg Loss",         f"[red]{a['avg_loss_pct']:.2f}%[/red]")
    t.add_row("Win / Loss Ratio", f"[cyan]{a['win_loss_ratio']:.3f}x[/cyan]")
    t.add_row("Wins",             str(a["n_wins"]))
    t.add_row("Losses",           str(a["n_losses"]))
    if a["outlier_count"]:
        t.add_row(
            f"Outlier losses ({a['outlier_count']})",
            f"[red]{a['outlier_impact_pct']:.2f}% total drag[/red]",
        )
    _console.print(t)

    # ── Loss distribution ─────────────────────────────────────────────────────
    if a.get("loss_distribution"):
        d = a["loss_distribution"]
        dt = Table(title="Loss Distribution", header_style="bold red", style="dim")
        dt.add_column("Percentile",    min_width=22)
        dt.add_column("Loss %",        justify="right")
        dt.add_row("Worst single",     f"[red]{d['worst']:.2f}%[/red]")
        dt.add_row("Bottom 10%",       f"[red]{d['p10']:.2f}%[/red]")
        dt.add_row("Bottom 25%",       f"[red]{d['p25']:.2f}%[/red]")
        dt.add_row("Median loss",      f"[yellow]{d['median']:.2f}%[/yellow]")
        dt.add_row("Mild losses (p75)",f"[yellow]{d['p75']:.2f}%[/yellow]")
        _console.print(dt)

    # ── Worst tickers ─────────────────────────────────────────────────────────
    if a.get("worst_tickers"):
        tt = Table(title="Worst Tickers by Avg Loss", header_style="bold yellow", style="dim")
        tt.add_column("Ticker",     min_width=10)
        tt.add_column("Avg Loss %", justify="right")
        tt.add_column("# Losses",   justify="right")
        for row in a["worst_tickers"]:
            tt.add_row(row["ticker"], f"[red]{row['avg_loss_pct']:.2f}%[/red]", str(int(row["count"])))
        _console.print(tt)

    # ── Quarterly breakdown ───────────────────────────────────────────────────
    if a.get("quarterly"):
        qt = Table(title="Quarterly Breakdown", header_style="bold magenta", style="dim")
        qt.add_column("Quarter",   min_width=10)
        qt.add_column("Trades",    justify="right")
        qt.add_column("Losses",    justify="right")
        qt.add_column("Loss Rate", justify="right")
        qt.add_column("Avg PnL %", justify="right")
        for row in a["quarterly"]:
            rate  = row["loss_rate"]
            color = "red" if rate > 50 else "yellow" if rate > 35 else "green"
            pnl_s = (
                f"[green]+{row['avg_pnl']:.2f}%[/green]"
                if row["avg_pnl"] > 0
                else f"[red]{row['avg_pnl']:.2f}%[/red]"
            )
            qt.add_row(
                row["quarter"],
                str(int(row["total"])),
                str(int(row["losses"])),
                f"[{color}]{rate:.1f}%[/{color}]",
                pnl_s,
            )
        _console.print(qt)
