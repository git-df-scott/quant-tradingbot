"""
Quant-Bot V1 — Small-Cap Momentum + Mean-Reversion Exit

Usage:
  python main.py --mode backtest    Run full historical backtest
  python main.py --mode simulate    30-day replay on MarketSimulator
  python main.py --mode paper       Live paper trading via Alpaca
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console

console = Console()


# ── Mode: backtest ─────────────────────────────────────────────────────────────

def run_backtest() -> None:
    from data.fetch import fetch_all
    from signals.momentum import generate_signals, signal_summary
    from backtest.engine import run as run_engine
    from reporting.report import generate_report

    console.rule("[bold cyan]BACKTEST MODE[/bold cyan]")

    console.print("[bold]Step 1/4[/bold] Fetching data...")
    price_data = fetch_all()

    if not price_data:
        console.print("[red]No data fetched. Aborting.[/red]")
        sys.exit(1)

    console.print(f"[bold]Step 2/4[/bold] Generating signals across {len(price_data)} tickers...")
    signals_df = generate_signals(price_data)
    signal_summary(signals_df)

    console.print("[bold]Step 3/4[/bold] Running backtest engine...")
    result = run_engine(price_data, signals_df)

    console.print("[bold]Step 4/4[/bold] Generating report...")
    generate_report(result)

    console.rule("[bold green]BUILD COMPLETE.[/bold green]")
    console.print("Run [bold cyan]`python main.py --mode backtest`[/bold cyan] to start.")


# ── Mode: simulate ─────────────────────────────────────────────────────────────

def run_simulate() -> None:
    from data.fetch import fetch_all
    from signals.momentum import generate_signals
    from simulation.market_sim import MarketSimulator
    from risk.manager import RiskManager
    import config

    console.rule("[bold cyan]SIMULATION MODE (30-day replay)[/bold cyan]")

    price_data = fetch_all()
    signals_df = generate_signals(price_data)

    sim = MarketSimulator(price_data=price_data)
    risk = RiskManager()

    for day_num in range(30):
        sim.step()
        pf = sim.get_portfolio()
        date = pf["date"]

        # Get signals for this date
        if date is not None and not signals_df.empty:
            day_sigs = signals_df[
                (signals_df["date"] == pd.Timestamp(date)) & (signals_df["signal"] == 1)
            ]
            for _, row in day_sigs.head(config.MAX_POSITIONS - len(pf["positions"])).iterrows():
                ticker = row["ticker"]
                price_info = sim.get_price(ticker)
                if price_info:
                    dollar_size = risk.size_position(pf["equity"], len(pf["positions"]))
                    qty = int(dollar_size / price_info["close"])
                    if qty > 0:
                        sim.submit_order(ticker, qty, "buy")
                        console.print(f"  [green]BUY {qty} {ticker} @ ~${price_info['close']:.2f}[/green]")

        # Advance to fill at next open
        console.print(
            f"  Day {day_num+1:2d} | {date} | Equity: ${pf['equity']:>12,.2f} | "
            f"Cash: ${pf['cash']:>10,.2f} | Positions: {len(pf['positions'])}"
        )

    console.print("\n[bold]Final portfolio:[/bold]")
    final = sim.get_portfolio()
    console.print(f"  Equity: ${final['equity']:,.2f}")
    console.print(f"  Positions: {list(final['positions'].keys())}")


# ── Mode: paper ────────────────────────────────────────────────────────────────

def run_paper() -> None:
    from data.fetch import fetch_all
    from signals.momentum import generate_signals
    from execution.paper_trader import PaperTrader
    from risk.manager import RiskManager
    import pandas as pd
    import config
    from datetime import date

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"paper_{date.today().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    console.rule("[bold cyan]PAPER TRADING MODE[/bold cyan]")
    console.print(f"Logging to {log_path}")

    trader = PaperTrader()
    risk   = RiskManager()

    price_data = fetch_all()
    signals_df = generate_signals(price_data)

    today = pd.Timestamp.today().normalize()
    today_sigs = signals_df[
        (signals_df["date"] == today) & (signals_df["signal"] == 1)
    ]

    portfolio = trader.get_portfolio()
    console.print(f"Current equity: ${portfolio.get('equity', 0):,.2f}")
    console.print(f"Signals today ({today.date()}): {len(today_sigs)}")

    for _, row in today_sigs.head(config.MAX_POSITIONS).iterrows():
        ticker = row["ticker"]
        price_info = trader.get_price(ticker)
        if not price_info:
            continue

        dollar_size = risk.size_position(
            portfolio.get("equity", config.INITIAL_CAPITAL),
            len(portfolio.get("positions", {}))
        )
        qty = int(dollar_size / price_info["close"])
        if qty <= 0:
            continue

        result = trader.submit_order(ticker, qty, "buy")
        msg = f"ORDER: BUY {qty} {ticker} @ ~${price_info['close']:.2f}"
        console.print(f"  [green]{msg}[/green]")
        logging.info(msg)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pandas as pd  # noqa: F401 — needed for simulate/paper inline usage

    parser = argparse.ArgumentParser(description="Quant-Bot V1")
    parser.add_argument(
        "--mode",
        choices=["backtest", "simulate", "paper"],
        default="backtest",
        help="Execution mode",
    )
    args = parser.parse_args()

    if args.mode == "backtest":
        run_backtest()
    elif args.mode == "simulate":
        run_simulate()
    elif args.mode == "paper":
        run_paper()
