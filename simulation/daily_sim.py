"""
Live-forward daily simulation.

Run once per trading day at 9:35am ET (after open):
  1. Check market calendar — exit early on holidays/weekends
  2. Load persisted state (cash, open positions, pending entries, cooldowns)
  3. Fetch 90-day OHLCV history for signal computation
  4. Fill pending entries from yesterday's signal at TODAY's open
  5. Check open positions for SL/TP using YESTERDAY's intraday H/L
  6. Generate new entry signals from YESTERDAY's close
  7. Queue valid signals as pending entries (fill tomorrow at open)
  8. Save state, write dated log, append to weekly_summary.csv
  9. Print daily summary

No look-ahead bias: signal_date close → fill at next open, exactly
matching the backtest engine's bar-t/bar-t+1 convention.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import date as Date
from pathlib import Path

import pandas as pd
import yfinance as yf

import config
from risk.manager import RiskManager
from signals.momentum import generate_signals

LOG_DIR      = Path("logs")
STATE_FILE   = LOG_DIR / "sim_state.json"
SUMMARY_FILE = LOG_DIR / "weekly_summary.csv"
INITIAL_CAPITAL = 10_000.0


# ── Market calendar ────────────────────────────────────────────────────────────

def _is_market_open(today: pd.Timestamp) -> bool:
    try:
        import pandas_market_calendars as mcal  # type: ignore
        nyse = mcal.get_calendar("NYSE")
        sched = nyse.schedule(
            start_date=today.strftime("%Y-%m-%d"),
            end_date=today.strftime("%Y-%m-%d"),
        )
        return not sched.empty
    except ImportError:
        return today.weekday() < 5


def _prev_trading_day(today: pd.Timestamp) -> pd.Timestamp:
    """Most recently completed trading session before today."""
    try:
        import pandas_market_calendars as mcal  # type: ignore
        nyse  = mcal.get_calendar("NYSE")
        start = (today - pd.Timedelta(days=14)).strftime("%Y-%m-%d")
        end   = (today - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        sched = nyse.schedule(start_date=start, end_date=end)
        return sched.index[-1].normalize()
    except (ImportError, IndexError):
        d = today - pd.Timedelta(days=1)
        while d.weekday() >= 5:
            d -= pd.Timedelta(days=1)
        return d


# ── State persistence ──────────────────────────────────────────────────────────

def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "cash":            INITIAL_CAPITAL,
        "initial_capital": INITIAL_CAPITAL,
        "start_date":      Date.today().isoformat(),
        "open_positions":  {},  # {ticker: {shares, entry_price, entry_date, peak_price}}
        "pending_entries": [],  # [{ticker, dollar_size}]
        "cooldown_until":  {},  # {ticker: "YYYY-MM-DD"}
        "total_pnl":       0.0,
        "total_trades":    0,
    }


def _save_state(state: dict) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, indent=2, default=str), encoding="utf-8"
    )


# ── Data helpers ───────────────────────────────────────────────────────────────

def _fetch_history() -> dict[str, pd.DataFrame]:
    from data.fetch import fetch_all
    return fetch_all(lookback_days=90, force_refresh=True)


def _fetch_todays_opens(
    tickers: list[str], today: pd.Timestamp
) -> dict[str, float]:
    """Download today's opening prices (available ~9:35am ET)."""
    today_str    = today.strftime("%Y-%m-%d")
    tomorrow_str = (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    opens: dict[str, float] = {}
    try:
        raw = yf.download(
            tickers,
            start=today_str, end=tomorrow_str,
            interval="1d", auto_adjust=True,
            progress=False, threads=True,
        )
        if raw.empty:
            return opens
        if isinstance(raw.columns, pd.MultiIndex):
            open_df = raw["Open"]
            for t in tickers:
                if t in open_df.columns:
                    val = open_df[t].dropna()
                    if not val.empty and val.iloc[0] > 0:
                        opens[t] = float(val.iloc[0])
        else:
            if not raw.empty and "Open" in raw.columns:
                val = raw["Open"].dropna()
                if not val.empty and val.iloc[0] > 0:
                    opens[tickers[0]] = float(val.iloc[0])
    except Exception as exc:
        logging.warning("Failed fetching today's opens: %s", exc)
    return opens


def _fail_reason(row: pd.Series) -> str:
    """Explain why a signal=0 row didn't fire."""
    reasons = []
    rank = row.get("momentum_rank", 0) or 0
    if rank < config.MOMENTUM_PERCENTILE:
        reasons.append(f"momentum_rank={rank:.3f}<{config.MOMENTUM_PERCENTILE}")
    pct = row.get("pct_from_5ma")
    if pct is not None and pct > 0:
        reasons.append(f"above_5ma={pct:+.3f}")
    vol = row.get("volume_ratio")
    if vol is not None and vol < config.VOLUME_MULTIPLIER:
        reasons.append(f"vol_ratio={vol:.2f}<{config.VOLUME_MULTIPLIER}")
    return " | ".join(reasons) if reasons else "NaN/unknown"


# ── Core daily run ─────────────────────────────────────────────────────────────

def run_daily() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    today = pd.Timestamp.today().normalize()

    log_path = LOG_DIR / f"paper_{today.strftime('%Y%m%d')}.log"
    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        force=True,
    )
    log = logging.getLogger("daily_sim")

    # ── 1. Calendar check ────────────────────────────────────────────────────
    if not _is_market_open(today):
        msg = f"Market closed today ({today.date()}) — no run."
        print(msg)
        log.info(msg)
        return

    signal_date = _prev_trading_day(today)
    log.info("=== Run: today=%s  signal_date=%s ===", today.date(), signal_date.date())
    print(f"\n{'='*62}")
    print(f"  Daily Sim | run={today.date()} | signal_date={signal_date.date()}")
    print(f"{'='*62}")

    # ── 2. Load state ────────────────────────────────────────────────────────
    state          = _load_state()
    cash           = float(state["cash"])
    open_positions: dict = state["open_positions"]
    pending        = list(state["pending_entries"])
    cooldown_until: dict = state["cooldown_until"]
    total_pnl      = float(state["total_pnl"])
    total_trades   = int(state["total_trades"])

    # ── 3. Fetch data ────────────────────────────────────────────────────────
    log.info("Fetching historical price data...")
    price_data = _fetch_history()
    if not price_data:
        log.error("No price data — aborting.")
        print("[ERROR] No price data returned.")
        return

    tickers      = list(price_data.keys())
    close_df     = pd.DataFrame({t: df["Close"] for t, df in price_data.items()}).sort_index()
    high_df      = pd.DataFrame({t: df["High"]  for t, df in price_data.items()}).sort_index()
    low_df       = pd.DataFrame({t: df["Low"]   for t, df in price_data.items()}).sort_index()

    # Resolve actual signal date — latest available bar <= signal_date
    available = close_df.index[close_df.index.normalize() <= signal_date]
    if available.empty:
        log.error("No data for signal_date %s", signal_date.date())
        print(f"[ERROR] No data available for {signal_date.date()}")
        return
    sd = available[-1]  # actual signal date timestamp

    log.info("Using signal bar: %s", sd.date())

    # Today's opens for filling pending entries
    log.info("Fetching today's opens for %d tickers...", len(tickers))
    todays_opens = _fetch_todays_opens(tickers, today)
    log.info("Got opens for %d tickers.", len(todays_opens))

    risk         = RiskManager(initial_capital=INITIAL_CAPITAL)
    daily_pnl    = 0.0
    trades_today = 0
    today_str    = today.date().isoformat()
    filled_today: set[str] = set()
    still_pending: list[dict] = []

    # ── 4. Fill pending entries at today's open ──────────────────────────────
    log.info("--- Processing %d pending entries ---", len(pending))
    for entry in pending:
        ticker    = entry["ticker"]
        dollar_sz = float(entry["dollar_size"])

        # Cooldown
        cd = cooldown_until.get(ticker, "")
        if cd and today_str <= cd:
            log.info("SKIP-FILL %s: cooldown until %s", ticker, cd)
            still_pending.append(entry)
            continue

        open_px = todays_opens.get(ticker)
        if open_px is None or open_px <= 0:
            log.warning("SKIP-FILL %s: no open price — carrying forward", ticker)
            still_pending.append(entry)
            continue

        eff_entry = open_px * (1 + config.SLIPPAGE)
        shares    = dollar_sz / eff_entry
        cost      = shares * eff_entry * (1 + config.COMMISSION)

        if cash < cost:
            log.warning("SKIP-FILL %s: need $%.2f, have $%.2f", ticker, cost, cash)
            continue

        cash -= cost
        open_positions[ticker] = {
            "shares":      shares,
            "entry_price": eff_entry,
            "entry_date":  today_str,
            "peak_price":  eff_entry,
        }
        filled_today.add(ticker)
        trades_today += 1

        msg = (f"FILLED  {ticker:6s}: {shares:.4f} sh @ ${eff_entry:.2f}  "
               f"cost=${cost:.2f}  slip=${(eff_entry - open_px)*shares:.2f}")
        log.info(msg)
        print(f"  [BUY ] {msg}")

    # ── 5. SL/TP check using yesterday's intraday H/L ────────────────────────
    log.info("--- Checking exits for %d open positions ---", len(open_positions))
    to_close: list[tuple[str, float, str]] = []

    for ticker, pos in list(open_positions.items()):
        if ticker in filled_today:
            log.info("HOLD    %s: just entered today", ticker)
            continue

        entry_px = float(pos["entry_price"])
        peak_px  = float(pos["peak_price"])
        shares   = float(pos["shares"])

        try:
            day_high  = float(high_df.loc[sd, ticker])
            day_low   = float(low_df.loc[sd, ticker])
            day_close = float(close_df.loc[sd, ticker])
        except (KeyError, TypeError, ValueError):
            log.warning("No H/L for %s on %s — skipping exit check", ticker, sd.date())
            continue

        if pd.isna(day_high) or pd.isna(day_low):
            log.warning("NaN H/L for %s on %s — skipping", ticker, sd.date())
            continue

        # Update running peak with intraday high
        pos["peak_price"] = max(peak_px, day_high)
        peak_px = pos["peak_price"]

        stop_px  = risk.stop_price(entry_px)
        tp_px    = entry_px * (1.0 + config.TAKE_PROFIT_PCT)
        trail_px = risk.trail_stop_price(peak_px)

        stop_hit   = day_low <= stop_px
        dollar_hit = shares * (entry_px - day_low) >= config.HARD_STOP_DOLLAR
        tp_hit     = day_high >= tp_px
        trail_act  = (peak_px - entry_px) / entry_px >= config.TRAILING_STOP_ACTIVATE_PCT
        trail_hit  = trail_act and day_low <= trail_px

        exit_px: float | None = None
        reason:  str | None   = None

        if stop_hit or dollar_hit:
            exit_px = stop_px
            reason  = "stop_loss"
            log.info("STOP    %s: low=%.2f <= stop=%.2f", ticker, day_low, stop_px)
        elif trail_hit:
            exit_px = trail_px
            reason  = "trailing_stop"
            log.info("TRAIL   %s: low=%.2f <= trail=%.2f (peak=%.2f)", ticker, day_low, trail_px, peak_px)
        elif tp_hit:
            exit_px = tp_px
            reason  = "take_profit"
            log.info("TP      %s: high=%.2f >= tp=%.2f", ticker, day_high, tp_px)
        else:
            log.info(
                "HOLD    %s: close=%.2f  entry=%.2f  peak=%.2f  stop=%.2f  tp=%.2f",
                ticker, day_close, entry_px, peak_px, stop_px, tp_px,
            )

        if exit_px is not None:
            to_close.append((ticker, exit_px, reason))  # type: ignore[arg-type]

    for ticker, raw_exit, reason in to_close:
        pos      = open_positions.pop(ticker)
        shares   = float(pos["shares"])
        entry_px = float(pos["entry_price"])

        eff_exit  = raw_exit * (1.0 - config.SLIPPAGE)
        proceeds  = shares * eff_exit * (1.0 - config.COMMISSION)
        cash     += proceeds

        pnl_d     = (eff_exit - entry_px) * shares
        pnl_pct   = (eff_exit - entry_px) / entry_px * 100.0
        daily_pnl += pnl_d
        total_pnl += pnl_d
        trades_today += 1
        total_trades += 1

        if reason == "stop_loss":
            cd_date = (today + pd.Timedelta(days=config.COOLDOWN_BARS + 1)).date().isoformat()
            cooldown_until[ticker] = cd_date

        msg = (f"CLOSED  {ticker:6s} [{reason}]: {shares:.4f} sh @ ${eff_exit:.2f}  "
               f"P&L=${pnl_d:+.2f} ({pnl_pct:+.2f}%)  entry=${entry_px:.2f}")
        log.info(msg)
        print(f"  [EXIT] {msg}")

    # ── 6. Generate signals from signal_date's close ─────────────────────────
    log.info("--- Generating signals for %s ---", sd.date())
    try:
        signals_df = generate_signals(price_data)
    except Exception as exc:
        log.error("Signal generation failed: %s", exc)
        signals_df = pd.DataFrame()

    sd_norm = sd.normalize()
    new_pending: list[dict] = []

    if not signals_df.empty:
        day_rows = signals_df[signals_df["date"].dt.normalize() == sd_norm].copy()
        n_open   = len(open_positions)

        # Log every evaluated ticker (pass and fail)
        log.info("--- Signal evaluation: %d candidates ---", len(day_rows))
        for _, row in day_rows.iterrows():
            if row["signal"] == 1:
                log.info(
                    "EVAL-PASS %s: rank=%.3f  vol_ratio=%s  pct_from_5ma=%s",
                    row["ticker"],
                    row.get("momentum_rank", 0),
                    f"{row.get('volume_ratio', 0):.2f}" if row.get("volume_ratio") else "?",
                    f"{row.get('pct_from_5ma', 0):.3f}" if row.get("pct_from_5ma") is not None else "?",
                )
            else:
                log.info(
                    "EVAL-FAIL %s: rank=%.3f  reason=[%s]",
                    row["ticker"],
                    row.get("momentum_rank", 0),
                    _fail_reason(row),
                )

        # Process signal=1 rows for new entries
        fired = day_rows[day_rows["signal"] == 1].sort_values("momentum_rank", ascending=False)
        log.info("--- %d signals fired ---", len(fired))

        for _, row in fired.iterrows():
            ticker = row["ticker"]

            if ticker in open_positions:
                log.info("SKIP-SIG %s: already in position", ticker)
                continue
            if any(e["ticker"] == ticker for e in still_pending + new_pending):
                log.info("SKIP-SIG %s: already pending", ticker)
                continue
            cd = cooldown_until.get(ticker, "")
            if cd and today_str <= cd:
                log.info("SKIP-SIG %s: cooldown until %s", ticker, cd)
                continue
            if n_open + len(new_pending) >= config.MAX_POSITIONS:
                log.info("SKIP-SIG %s: max positions (%d) reached", ticker, config.MAX_POSITIONS)
                continue

            # Portfolio equity for sizing
            pos_val = sum(
                float(p["shares"]) * float(close_df.loc[sd, t])
                for t, p in open_positions.items()
                if t in close_df.columns and not pd.isna(close_df.loc[sd, t])
            )
            equity = cash + pos_val
            dollar_sz = risk.size_position(equity, n_open + len(new_pending))
            if dollar_sz <= 0:
                log.info("SKIP-SIG %s: zero size (equity=%.2f)", ticker, equity)
                continue

            new_pending.append({"ticker": ticker, "dollar_size": dollar_sz})
            log.info(
                "QUEUED  %s: rank=%.3f  size=$%.2f → fill tomorrow at open",
                ticker, row.get("momentum_rank", 0), dollar_sz,
            )
            print(f"  [SIG ] {ticker:6s}  rank={row.get('momentum_rank', 0):.3f}  "
                  f"size=${dollar_sz:.0f} → queued for tomorrow")
    else:
        log.info("No signals generated.")

    # ── 7. Compute portfolio equity ──────────────────────────────────────────
    pos_val = 0.0
    for ticker, pos in open_positions.items():
        if ticker in close_df.columns:
            try:
                px = float(close_df.loc[sd, ticker])
                if not pd.isna(px):
                    pos_val += float(pos["shares"]) * px
            except KeyError:
                pass
    equity = cash + pos_val

    # ── 8. Persist state ─────────────────────────────────────────────────────
    state["cash"]            = cash
    state["open_positions"]  = {
        k: {
            "shares":      float(v["shares"]),
            "entry_price": float(v["entry_price"]),
            "entry_date":  v["entry_date"],
            "peak_price":  float(v["peak_price"]),
        }
        for k, v in open_positions.items()
    }
    state["pending_entries"] = still_pending + new_pending
    state["cooldown_until"]  = cooldown_until
    state["total_pnl"]       = total_pnl
    state["total_trades"]    = total_trades
    _save_state(state)

    # ── 9. Print summary ──────────────────────────────────────────────────────
    initial_cap = float(state["initial_capital"])
    ret_pct     = (equity - initial_cap) / initial_cap * 100.0
    pending_all = still_pending + new_pending

    lines = [
        f"\n{'-'*62}",
        f"  DATE         : {today.date()}",
        f"  CASH         : ${cash:>12,.2f}",
        f"  POSITION VAL : ${pos_val:>12,.2f}",
        f"  EQUITY       : ${equity:>12,.2f}",
        f"  OPEN POS     : {len(open_positions)} held  |  {len(pending_all)} pending",
        f"  DAILY P&L    : ${daily_pnl:>+12,.2f}",
        f"  TOTAL P&L    : ${total_pnl:>+12,.2f}  ({ret_pct:+.2f}%)",
        f"  TRADES TODAY : {trades_today}",
        f"{'-'*62}",
    ]
    summary = "\n".join(lines)
    print(summary)
    log.info(summary)

    # ── 10. Append to weekly_summary.csv ──────────────────────────────────────
    _append_summary(
        date=today_str,
        cash=cash,
        open_positions=len(open_positions),
        daily_pnl=daily_pnl,
        total_pnl=total_pnl,
        trades_today=trades_today,
    )


def _append_summary(
    date: str, cash: float, open_positions: int,
    daily_pnl: float, total_pnl: float, trades_today: int,
) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    write_header = not SUMMARY_FILE.exists()
    with open(SUMMARY_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["date", "cash", "open_positions", "daily_pnl", "total_pnl", "trades_today"])
        w.writerow([
            date,
            round(cash, 2),
            open_positions,
            round(daily_pnl, 2),
            round(total_pnl, 2),
            trades_today,
        ])
