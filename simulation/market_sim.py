"""
In-memory market simulator — replays historical data, no API required.
Interface is identical to PaperTrader; swap one for the other with one line.

reset() fully clears all state: positions, orders, cash, date.
"""

from __future__ import annotations

from datetime import date as Date
from dataclasses import dataclass, field

import pandas as pd

import config
from data.fetch import fetch_all


@dataclass
class Order:
    ticker: str
    qty: float
    side: str          # "buy" | "sell"
    submitted_date: Date
    filled: bool = False
    fill_price: float = 0.0
    fill_date: Date | None = None


class MarketSimulator:
    def __init__(
        self,
        price_data: dict[str, pd.DataFrame] | None = None,
        start_date: str | None = None,
        initial_capital: float = config.INITIAL_CAPITAL,
    ) -> None:
        self._price_data  = price_data or fetch_all()
        self._initial_cap = initial_capital

        # Build close/open DataFrames
        self._close_df = pd.DataFrame({t: df["Close"] for t, df in self._price_data.items()}).sort_index()
        self._open_df  = pd.DataFrame({t: df["Open"]  for t, df in self._price_data.items()}).sort_index()
        self._dates    = list(self._close_df.index)

        # Determine start index
        if start_date:
            start_ts = pd.Timestamp(start_date)
            self._start_idx = next(
                (i for i, d in enumerate(self._dates) if d >= start_ts), 0
            )
        else:
            self._start_idx = max(0, len(self._dates) - 30)

        self._default_start_idx = self._start_idx
        self.reset()

    # ── State management ─────────────────────────────────────────────────────

    def reset(self) -> None:
        """Fully wipe all state. Positions, orders, cash, and date reset."""
        self._current_idx  = self._default_start_idx
        self._cash         = self._initial_cap
        self._positions: dict[str, float] = {}   # {ticker: shares}
        self._orders: list[Order] = []
        self._order_history: list[Order] = []

        start = self._dates[self._current_idx] if self._dates else "N/A"
        print(f"Simulator reset. Date: {start}. Capital: ${self._cash:,.0f}")

    # ── Stepping ──────────────────────────────────────────────────────────────

    def step(self) -> None:
        """Advance one trading day. Fills pending orders at today's open."""
        if self._current_idx >= len(self._dates) - 1:
            print("Simulator reached end of data.")
            return

        self._current_idx += 1
        today = self._dates[self._current_idx]

        # Fill any pending orders at today's open
        for order in self._orders:
            if not order.filled:
                open_px = self._open_df.loc[today, order.ticker] \
                    if order.ticker in self._open_df.columns else None

                if open_px is None or pd.isna(open_px):
                    continue

                cost = order.qty * open_px
                if order.side == "buy":
                    if self._cash >= cost:
                        self._cash -= cost
                        self._positions[order.ticker] = self._positions.get(order.ticker, 0) + order.qty
                        order.filled     = True
                        order.fill_price = open_px
                        order.fill_date  = today
                elif order.side == "sell":
                    held = self._positions.get(order.ticker, 0)
                    qty  = min(order.qty, held)
                    if qty > 0:
                        self._cash += qty * open_px
                        self._positions[order.ticker] = held - qty
                        if self._positions[order.ticker] == 0:
                            del self._positions[order.ticker]
                        order.filled     = True
                        order.fill_price = open_px
                        order.fill_date  = today

        # Move filled orders to history
        filled   = [o for o in self._orders if o.filled]
        pending  = [o for o in self._orders if not o.filled]
        self._order_history.extend(filled)
        self._orders = pending

    # ── Market data ───────────────────────────────────────────────────────────

    def get_price(self, ticker: str) -> dict | None:
        """Return OHLCV dict for current day, or None if unavailable."""
        if self._current_idx >= len(self._dates):
            return None
        date = self._dates[self._current_idx]
        if ticker not in self._close_df.columns:
            return None
        try:
            return {
                "open":   self._open_df.loc[date, ticker],
                "close":  self._close_df.loc[date, ticker],
                "date":   date,
            }
        except KeyError:
            return None

    @property
    def current_date(self) -> pd.Timestamp | None:
        if self._current_idx < len(self._dates):
            return self._dates[self._current_idx]
        return None

    # ── Orders ────────────────────────────────────────────────────────────────

    def submit_order(self, ticker: str, qty: float, side: str) -> Order:
        """Record an order for next-bar fill. Returns the Order object."""
        today = self._dates[self._current_idx]
        order = Order(ticker=ticker, qty=qty, side=side, submitted_date=today)
        self._orders.append(order)
        return order

    # ── Portfolio ─────────────────────────────────────────────────────────────

    def get_portfolio(self) -> dict:
        """Return current positions, cash, and total equity."""
        date = self.current_date
        equity = self._cash

        positions_detail = {}
        for ticker, shares in self._positions.items():
            price = None
            if date is not None and ticker in self._close_df.columns:
                try:
                    price = self._close_df.loc[date, ticker]
                except KeyError:
                    pass
            mkt_val = shares * price if price else 0.0
            equity += mkt_val
            positions_detail[ticker] = {
                "shares":    shares,
                "price":     price,
                "mkt_value": mkt_val,
            }

        return {
            "date":      date,
            "cash":      self._cash,
            "equity":    equity,
            "positions": positions_detail,
            "orders_pending": len(self._orders),
        }
