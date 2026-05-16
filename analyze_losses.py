"""
Loss pattern analysis — reads results/backtest_cache.json and prints a
Rich report covering the four diagnostic questions. No strategy logic is
changed here.

Run:
    python analyze_losses.py
"""

import json
from pathlib import Path

import io
import sys

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich import box

CACHE = Path("results/backtest_cache.json")
# Force UTF-8 output so Rich box-drawing chars work on Windows terminals
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
console = Console(file=sys.stdout)


# ── Load data ─────────────────────────────────────────────────────────────────

def load() -> tuple[pd.DataFrame, pd.Series]:
    if not CACHE.exists():
        console.print("[red]No cache found. Run the backtest first.[/red]")
        raise SystemExit(1)

    raw = json.loads(CACHE.read_text(encoding="utf-8"))

    trades = pd.DataFrame(raw["trades"])
    trades["entry_date"] = pd.to_datetime(trades["entry_date"])
    trades["exit_date"]  = pd.to_datetime(trades["exit_date"])
    # pnl_pct is already stored as percentage (e.g. 2.547 means +2.547%)
    trades["win"] = trades["pnl_pct"] > 0

    spy_raw = pd.DataFrame(raw["spy_curve"])
    spy_raw["date"] = pd.to_datetime(spy_raw["date"])
    spy = spy_raw.set_index("date")["value"].sort_index()
    # Daily SPY return: pct_change gives (today - yesterday) / yesterday
    spy_ret = spy.pct_change().dropna()

    return trades, spy_ret


# ── 1. Avg win $ vs avg loss $ ────────────────────────────────────────────────

def print_dollar_summary(trades: pd.DataFrame) -> None:
    wins   = trades[trades["win"]]
    losses = trades[~trades["win"]]

    t = Table(
        title="[bold]1. Avg Win $ vs Avg Loss $[/bold]",
        box=box.SIMPLE_HEAVY, header_style="bold cyan", style="dim",
    )
    t.add_column("Cohort",          min_width=10)
    t.add_column("Count",           justify="right")
    t.add_column("Avg PnL $",       justify="right")
    t.add_column("Median PnL $",    justify="right")
    t.add_column("Worst $",         justify="right")
    t.add_column("Best $",          justify="right")
    t.add_column("Total PnL $",     justify="right")

    def row(label, subset, style):
        if subset.empty:
            t.add_row(label, "0", "—", "—", "—", "—", "—", style=style)
            return
        d = subset["pnl_dollar"]
        t.add_row(
            label,
            str(len(subset)),
            f"[{style}]${d.mean():+,.0f}[/{style}]",
            f"${d.median():+,.0f}",
            f"${d.min():+,.0f}",
            f"${d.max():+,.0f}",
            f"[{style}]${d.sum():+,.0f}[/{style}]",
            style=style,
        )

    row("Winners",  wins,   "green")
    row("Losers",   losses, "red")

    ratio = abs(wins["pnl_dollar"].mean() / losses["pnl_dollar"].mean()) if len(losses) else float("inf")
    t.add_section()
    t.add_row(
        "Win/Loss ratio",
        "", f"[cyan]{ratio:.2f}×[/cyan]", "", "", "", "",
    )

    console.print(t)
    console.print()


# ── 2. Hold duration: winners vs losers ───────────────────────────────────────

def print_duration_summary(trades: pd.DataFrame) -> None:
    wins   = trades[trades["win"]]
    losses = trades[~trades["win"]]

    t = Table(
        title="[bold]2. Hold Duration — Winners vs Losers[/bold]",
        box=box.SIMPLE_HEAVY, header_style="bold cyan", style="dim",
    )
    t.add_column("Cohort",      min_width=10)
    t.add_column("Avg days",    justify="right")
    t.add_column("Median days", justify="right")
    t.add_column("Min days",    justify="right")
    t.add_column("Max days",    justify="right")

    def dur_row(label, subset, style):
        if subset.empty:
            t.add_row(label, "—", "—", "—", "—")
            return
        d = subset["holding_days"]
        t.add_row(
            label,
            f"[{style}]{d.mean():.1f}[/{style}]",
            f"{d.median():.0f}",
            f"{d.min()}",
            f"{d.max()}",
        )

    dur_row("Winners",  wins,   "green")
    dur_row("Losers",   losses, "red")
    console.print(t)
    console.print()


# ── 3. Quick-exit losses (<= 2 days) ──────────────────────────────────────────

def print_quick_losses(trades: pd.DataFrame) -> None:
    losses  = trades[~trades["win"]]
    quick   = losses[losses["holding_days"] <= 2]
    slow    = losses[losses["holding_days"] >  2]

    t = Table(
        title="[bold]3. Losses Closed Within 1–2 Days[/bold]",
        box=box.SIMPLE_HEAVY, header_style="bold cyan", style="dim",
    )
    t.add_column("Bucket",          min_width=24)
    t.add_column("Count",           justify="right")
    t.add_column("% of all losses", justify="right")
    t.add_column("Avg loss $",      justify="right")
    t.add_column("Avg loss %",      justify="right")
    t.add_column("Avg hold days",   justify="right")

    total_losses = max(len(losses), 1)

    def qrow(label, subset, style):
        if subset.empty:
            t.add_row(label, "0", "0%", "—", "—", "—")
            return
        t.add_row(
            label,
            str(len(subset)),
            f"[{style}]{len(subset)/total_losses*100:.1f}%[/{style}]",
            f"[{style}]${subset['pnl_dollar'].mean():+,.0f}[/{style}]",
            f"[{style}]{subset['pnl_pct'].mean():.2f}%[/{style}]",
            f"{subset['holding_days'].mean():.1f}",
        )

    qrow("Quick losses  (<= 2 days)", quick, "red")
    qrow("Longer losses (> 2 days)", slow,  "yellow")

    console.print(t)

    # Detail table of every quick loss
    if not quick.empty:
        detail = Table(
            title="Quick-loss detail (<= 2 days)",
            box=box.MINIMAL, header_style="bold", style="dim",
        )
        detail.add_column("Ticker", style="cyan")
        detail.add_column("Entry date")
        detail.add_column("Exit date")
        detail.add_column("Days", justify="right")
        detail.add_column("PnL %",  justify="right")
        detail.add_column("PnL $",  justify="right")
        detail.add_column("Reason")

        for _, r in quick.sort_values("pnl_dollar").iterrows():
            detail.add_row(
                r["ticker"],
                str(r["entry_date"].date()),
                str(r["exit_date"].date()),
                str(int(r["holding_days"])),
                f"[red]{r['pnl_pct']:.2f}%[/red]",
                f"[red]${r['pnl_dollar']:+,.0f}[/red]",
                r["exit_reason"],
            )
        console.print(detail)

    console.print()


# ── 4. SPY direction on entry day of losing trades ────────────────────────────

def print_spy_correlation(trades: pd.DataFrame, spy_ret: pd.Series) -> None:
    losses = trades[~trades["win"]].copy()

    # Map each loss entry_date to SPY's return on that day
    losses["spy_ret"] = losses["entry_date"].map(spy_ret)
    matched = losses.dropna(subset=["spy_ret"])

    n_no_spy = len(losses) - len(matched)

    t = Table(
        title=f"[bold]4. SPY Direction on Loss-Trade Entry Days[/bold]"
              + (f"  [dim]({n_no_spy} losses outside SPY data window, excluded)[/dim]" if n_no_spy else ""),
        box=box.SIMPLE_HEAVY, header_style="bold cyan", style="dim",
    )
    t.add_column("SPY on entry day", min_width=20)
    t.add_column("# loss trades",  justify="right")
    t.add_column("% of matched",   justify="right")
    t.add_column("Avg loss %",     justify="right")
    t.add_column("Avg loss $",     justify="right")
    t.add_column("Avg SPY ret %",  justify="right")

    for label, subset, style in [
        ("SPY down  (< −0.3%)", matched[matched["spy_ret"] < -0.003], "red"),
        ("SPY flat  (−0.3%–+0.3%)", matched[matched["spy_ret"].between(-0.003, 0.003)], "yellow"),
        ("SPY up    (> +0.3%)", matched[matched["spy_ret"] > 0.003], "green"),
    ]:
        if subset.empty:
            t.add_row(label, "0", "—", "—", "—", "—")
            continue
        t.add_row(
            label,
            str(len(subset)),
            f"[{style}]{len(subset)/max(len(matched),1)*100:.1f}%[/{style}]",
            f"[{style}]{subset['pnl_pct'].mean():.2f}%[/{style}]",
            f"[{style}]${subset['pnl_dollar'].mean():+,.0f}[/{style}]",
            f"{subset['spy_ret'].mean()*100:+.2f}%",
        )

    console.print(t)

    # Pearson correlation: loss_pct vs SPY_ret on entry day
    if len(matched) >= 5:
        corr = matched["pnl_pct"].corr(matched["spy_ret"] * 100)
        console.print(
            f"  Pearson r (loss % vs SPY ret on entry): [cyan]{corr:.3f}[/cyan]"
            + ("  [green](positive = losses worse when SPY fell)[/green]"
               if corr > 0.1 else
               "  [yellow](weak or no correlation)[/yellow]"
               if abs(corr) <= 0.1 else
               "  [red](negative = losses worse when SPY rose — idiosyncratic)[/red]")
        )
    else:
        console.print("  [dim]Not enough matched trades for correlation.[/dim]")

    # Distribution of SPY returns on loss-entry days
    console.print()
    console.print("  SPY daily-return buckets on loss entry days:")
    buckets = [-0.03, -0.02, -0.01, 0, 0.01, 0.02, 0.03]
    labels_ = ["<-3%", "-3%->-2%", "-2%->-1%", "-1%->0%", "0%->+1%", "+1%->+2%", "+2%->+3%", ">+3%"]
    cuts = pd.cut(matched["spy_ret"], bins=[-np.inf] + buckets + [np.inf], labels=labels_)
    for bucket, cnt in cuts.value_counts().sort_index().items():
        bar = "█" * cnt
        color = "red" if bucket.startswith("<") or "->0" in bucket else "green"
        console.print(f"    [{color}]{bucket:>12}  {bar} {cnt}[/{color}]")

    console.print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    trades, spy_ret = load()

    console.rule("[bold cyan]Loss Pattern Analysis[/bold cyan]")
    console.print(
        f"  Loaded [cyan]{len(trades)}[/cyan] trades | "
        f"[green]{trades['win'].sum()} winners[/green] | "
        f"[red]{(~trades['win']).sum()} losers[/red] | "
        f"SPY data: {spy_ret.index[0].date()} -> {spy_ret.index[-1].date()}"
    )
    console.print()

    print_dollar_summary(trades)
    print_duration_summary(trades)
    print_quick_losses(trades)
    print_spy_correlation(trades, spy_ret)

    console.rule("[bold dim]End of analysis[/bold dim]")


if __name__ == "__main__":
    main()
