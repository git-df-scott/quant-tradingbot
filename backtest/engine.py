"""
Bar-by-bar backtesting engine.

Invariants:
  - Signals generated at close of bar t
  - Fills execute at open of bar t+1 (next open)
  - Stop-loss checked at close of each bar
  - Take-profit (close > 20-day MA) checked at close of each bar
  - No look-ahead bias: strategy only sees data[0:t+1] at bar t
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn

import config
from risk.manager import RiskManager

console = Console()


@dataclass
class BacktestResult:
    equity_curve: pd.Series          # DatetimeIndex → portfolio value
    trades: pd.DataFrame             # one row per closed trade
    metrics: dict                    # performance statistics
    open_df: pd.DataFrame            # open prices (wide)
    close_df: pd.DataFrame           # close prices (wide)
    ma20_df: pd.DataFrame            # 20-day MA (wide)


def _build_wide(price_data: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    closes = {t: df["Close"] for t, df in price_data.items()}
    opens  = {t: df["Open"]  for t, df in price_data.items()}

    close_df = pd.DataFrame(closes).sort_index()
    open_df  = pd.DataFrame(opens).sort_index()

    idx = close_df.index.intersection(open_df.index)
    close_df = close_df.loc[idx]
    open_df  = open_df.loc[idx]

    ma20_df = close_df.rolling(config.EXIT_MA_WINDOW, min_periods=config.EXIT_MA_WINDOW).mean()

    return open_df, close_df, ma20_df


def _compute_metrics(
    equity: pd.Series,
    trades: pd.DataFrame,
    initial_capital: float,
    rf_rate: float = config.RISK_FREE_RATE,
) -> dict:
    if len(equity) < 2:
        return {}

    total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
    n_years = len(equity) / 252
    annual_return = (1 + total_return) ** (1 / max(n_years, 1e-9)) - 1

    daily_ret = equity.pct_change().dropna()
    excess    = daily_ret - rf_rate / 252
    sharpe    = (excess.mean() / excess.std()) * np.sqrt(252) if excess.std() > 1e-10 else 0.0

    rolling_max = equity.cummax()
    drawdown    = (equity - rolling_max) / rolling_max
    max_dd      = drawdown.min()

    if trades.empty:
        return {
            "total_return_pct":      round(total_return * 100, 2),
            "annualized_return_pct": round(annual_return * 100, 2),
            "max_drawdown_pct":      round(max_dd * 100, 2),
            "sharpe_ratio":          round(sharpe, 3),
            "win_rate_pct":          None,
            "avg_win_pct":           None,
            "avg_loss_pct":          None,
            "profit_factor":         None,
            "total_trades":          0,
            "avg_holding_days":      None,
        }

    wins   = trades[trades["pnl_pct"] > 0]
    losses = trades[trades["pnl_pct"] <= 0]

    win_rate   = len(wins) / len(trades)
    avg_win    = wins["pnl_pct"].mean()    if len(wins)   > 0 else 0.0
    avg_loss   = losses["pnl_pct"].mean()  if len(losses) > 0 else 0.0

    gross_profit = wins["pnl_pct"].sum()
    gross_loss   = abs(losses["pnl_pct"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else None  # None → null (no losses)

    avg_holding = trades["holding_days"].mean() if "holding_days" in trades.columns else 0.0

    return {
        "total_return_pct":      round(total_return * 100, 2),
        "annualized_return_pct": round(annual_return * 100, 2),
        "max_drawdown_pct":      round(max_dd * 100, 2),
        "sharpe_ratio":          round(sharpe, 3),
        "win_rate_pct":          round(win_rate * 100, 2),
        "avg_win_pct":           round(avg_win * 100, 2),
        "avg_loss_pct":          round(avg_loss * 100, 2),
        "profit_factor":         round(profit_factor, 3) if profit_factor is not None else None,
        "total_trades":          len(trades),
        "avg_holding_days":      round(avg_holding, 1),
    }


def run(
    price_data: dict[str, pd.DataFrame],
    signals_df: pd.DataFrame,
    risk_manager: RiskManager | None = None,
    initial_capital: float = config.INITIAL_CAPITAL,
    commission: float = config.COMMISSION,
    pre_window_bars: dict[str, int] | None = None,
    spy_regime: pd.Series | None = None,
) -> BacktestResult:
    """
    Execute bar-by-bar backtest.

    Args:
        price_data      : {ticker: OHLCV DataFrame} — may be a date-filtered window
        signals_df      : output of signals.momentum.generate_signals()
        risk_manager    : RiskManager instance (created with defaults if None)
        initial_capital : starting cash
        commission      : fractional cost per trade (both sides)
        pre_window_bars : {ticker: int} bars available in FULL history before this window.
                          Used to correctly enforce MIN_BARS_BEFORE_ENTRY when price_data
                          is a trimmed window (e.g. date-range backtests).

    Returns:
        BacktestResult with equity curve, trades, and metrics.
    """
    if risk_manager is None:
        risk_manager = RiskManager(initial_capital=initial_capital)

    open_df, close_df, ma20_df = _build_wide(price_data)
    dates  = list(close_df.index)
    tickers = list(close_df.columns)

    if not dates:
        empty = pd.Series([], dtype=float, name="portfolio_value")
        return BacktestResult(
            equity_curve=empty,
            trades=pd.DataFrame(),
            metrics={},
            open_df=open_df,
            close_df=close_df,
            ma20_df=ma20_df,
        )

    # Regime diagnostics
    if spy_regime is None:
        print("[regime-engine] spy_regime=None — all days default to bull")
    elif spy_regime.empty:
        print("[regime-engine] spy_regime is EMPTY — all days default to bull (SPY fetch may have failed)")
    else:
        counts = spy_regime.value_counts().to_dict()
        print(f"[regime-engine] spy_regime OK: {counts}")

    # Index signals by date for fast lookup
    sig_by_date: dict[pd.Timestamp, pd.DataFrame] = {}
    if not signals_df.empty:
        for date, grp in signals_df.groupby("date"):
            sig_by_date[pd.Timestamp(date)] = grp[grp["signal"] == 1].copy()

    cash: float = initial_capital
    open_positions: dict[str, dict] = {}
    equity_curve: list[tuple] = []
    all_trades: list[dict] = []
    # cooldown_until[ticker] = bar index after which the ticker may be re-entered
    cooldown_until: dict[str, int] = {}
    _bear_blocks: int = 0

    # Pre-compute per-ticker bar counts for the 60-bar minimum check
    ticker_bar_counts: dict[str, list[pd.Timestamp]] = {
        t: list(close_df[t].dropna().index)
        for t in close_df.columns
    }

    with Progress(SpinnerColumn(spinner_name="line"), "[progress.description]{task.description}", TimeElapsedColumn(), console=console) as progress:
        task = progress.add_task("[cyan]Running backtest...", total=len(dates))

        for i, date in enumerate(dates):
            progress.advance(task)

            # ── Mark-to-market: portfolio value at today's close ──────────────
            position_value = 0.0
            for ticker, pos in open_positions.items():
                if ticker in close_df.columns:
                    cp = close_df.loc[date, ticker]
                    if not pd.isna(cp):
                        pos["current_price"] = cp
                        pos["peak_price"] = max(pos["peak_price"], cp)
                        position_value += pos["shares"] * cp

            portfolio_value = cash + position_value
            equity_curve.append((date, portfolio_value))

            # ── Check exits for all open positions ────────────────────────────
            to_exit: list[str] = []
            for ticker, pos in open_positions.items():
                if ticker not in close_df.columns:
                    continue

                close_px = close_df.loc[date, ticker]
                if pd.isna(close_px):
                    continue

                entry_px  = pos["entry_price"]
                peak_px   = pos["peak_price"]
                shares    = pos["shares"]

                stop_hit     = risk_manager.check_stop(entry_px, close_px)
                dollar_hit   = risk_manager.check_hard_dollar_stop(entry_px, close_px, shares)
                trail_hit    = risk_manager.check_trailing_stop(entry_px, peak_px, close_px)
                tp_hit       = risk_manager.check_take_profit(entry_px, close_px)

                if stop_hit or dollar_hit:
                    pos["exit_reason"] = "stop_loss" if stop_hit else "hard_dollar_stop"
                    pos["exit_price"]  = max(close_px, risk_manager.stop_price(entry_px))
                    to_exit.append(ticker)
                elif trail_hit:
                    pos["exit_reason"] = "trailing_stop"
                    pos["exit_price"]  = close_px
                    to_exit.append(ticker)
                elif tp_hit:
                    pos["exit_reason"] = "take_profit"
                    pos["exit_price"]  = close_px
                    to_exit.append(ticker)

            for ticker in to_exit:
                pos = open_positions.pop(ticker)
                exit_px  = pos["exit_price"]
                proceeds = pos["shares"] * exit_px * (1 - commission)
                cash += proceeds

                pnl_pct = (exit_px - pos["entry_price"]) / pos["entry_price"]
                holding = (date - pos["entry_date"]).days

                all_trades.append({
                    "ticker":       ticker,
                    "entry_date":   pos["entry_date"],
                    "entry_price":  pos["entry_price"],
                    "exit_date":    date,
                    "exit_price":   exit_px,
                    "exit_reason":  pos["exit_reason"],
                    "shares":       pos["shares"],
                    "pnl_pct":      pnl_pct,
                    "pnl_dollar":   (exit_px - pos["entry_price"]) * pos["shares"],
                    "holding_days": holding,
                })

                # Cooldown: ban re-entry after any stop-type exit
                if pos["exit_reason"] in ("stop_loss", "hard_dollar_stop"):
                    cooldown_until[ticker] = i + config.COOLDOWN_BARS + 1

            # ── Process entries from yesterday's signals (fill at today's open) ──
            if i > 0:
                prev_date = dates[i - 1]

                # ── Market regime gate ────────────────────────────────────────
                regime = "bull"
                if spy_regime is not None and not spy_regime.empty:
                    r = spy_regime.get(pd.Timestamp(prev_date))
                    if r is not None and not (isinstance(r, float) and pd.isna(r)):
                        regime = str(r)

                # Death cross: no new entries at all
                if regime == "bear":
                    day_sigs = sig_by_date.get(pd.Timestamp(prev_date), pd.DataFrame())
                    _bear_blocks += len(day_sigs)

                else:
                    day_signals = sig_by_date.get(pd.Timestamp(prev_date), pd.DataFrame())

                    if not day_signals.empty:
                        if regime == "caution":
                            pos_cap    = config.REGIME_CAUTION_MAX_POSITIONS
                            size_mult  = config.REGIME_CAUTION_SIZE_MULT
                            min_rank   = config.REGIME_CAUTION_MOMENTUM_PERCENTILE
                            min_vol    = config.REGIME_CAUTION_VOLUME_MULTIPLIER
                        else:
                            pos_cap    = config.MAX_POSITIONS
                            size_mult  = 1.0
                            min_rank   = 0.0
                            min_vol    = 0.0  # bull: no extra volume gate beyond signal pre-screen

                        available_slots = pos_cap - len(open_positions)

                        filtered = day_signals[day_signals["momentum_rank"] >= min_rank]
                        if min_vol > 0 and "volume_ratio" in filtered.columns:
                            filtered = filtered[filtered["volume_ratio"].fillna(0) >= min_vol]

                        candidates = (
                            filtered
                            .sort_values("momentum_rank", ascending=False)
                            .head(available_slots)
                        )

                        for _, row in candidates.iterrows():
                            ticker = row["ticker"]

                            if ticker in open_positions:
                                continue
                            if ticker not in open_df.columns:
                                continue

                            # Cooldown check
                            if cooldown_until.get(ticker, 0) > i:
                                continue

                            fill_px = open_df.loc[date, ticker] if date in open_df.index else np.nan
                            if pd.isna(fill_px) or fill_px <= 0:
                                continue

                            # 60-bar minimum: enough history for reliable signals.
                            # pre_window_bars accounts for history before a trimmed window.
                            in_window = sum(
                                1 for t in ticker_bar_counts.get(ticker, []) if t < date
                            )
                            pre_window = (pre_window_bars or {}).get(ticker, 0)
                            if in_window + pre_window < config.MIN_BARS_BEFORE_ENTRY:
                                continue

                            # Recompute portfolio value for correct sizing
                            pos_val = sum(
                                p["shares"] * p.get("current_price", p["entry_price"])
                                for p in open_positions.values()
                            )
                            pv = cash + pos_val

                            dollar_size = risk_manager.size_position(pv, len(open_positions)) * size_mult
                            if dollar_size <= 0:
                                continue

                            shares = dollar_size / fill_px
                            cost   = shares * fill_px * (1 + commission)

                            if cash < cost:
                                continue

                            cash -= cost
                            open_positions[ticker] = {
                                "entry_price":   fill_px,
                                "peak_price":    fill_px,
                                "shares":        shares,
                                "entry_date":    date,
                                "current_price": fill_px,
                            }

    print(f"[regime-engine] bear-blocked entry attempts: {_bear_blocks}")

    # ── Close remaining positions at last close ───────────────────────────────
    last_date = dates[-1]
    for ticker, pos in open_positions.items():
        if ticker in close_df.columns:
            last_px  = close_df.loc[last_date, ticker]
            proceeds = pos["shares"] * last_px * (1 - commission)
            cash += proceeds
            pnl_pct = (last_px - pos["entry_price"]) / pos["entry_price"]
            all_trades.append({
                "ticker":       ticker,
                "entry_date":   pos["entry_date"],
                "entry_price":  pos["entry_price"],
                "exit_date":    last_date,
                "exit_price":   last_px,
                "exit_reason":  "end_of_backtest",
                "shares":       pos["shares"],
                "pnl_pct":      pnl_pct,
                "pnl_dollar":   (last_px - pos["entry_price"]) * pos["shares"],
                "holding_days": (last_date - pos["entry_date"]).days,
            })

    equity_series = pd.Series(
        [v for _, v in equity_curve],
        index=pd.DatetimeIndex([d for d, _ in equity_curve]),
        name="portfolio_value",
    )

    trades_df = pd.DataFrame(all_trades)
    metrics   = _compute_metrics(equity_series, trades_df, initial_capital)

    return BacktestResult(
        equity_curve=equity_series,
        trades=trades_df,
        metrics=metrics,
        open_df=open_df,
        close_df=close_df,
        ma20_df=ma20_df,
    )
