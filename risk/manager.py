"""
Pre-trade risk checks and position sizing.
All methods are pure functions of the inputs — no side effects.
"""

from __future__ import annotations

import config


class RiskManager:
    def __init__(
        self,
        initial_capital: float = config.INITIAL_CAPITAL,
        max_positions: int = config.MAX_POSITIONS,
        position_size_pct: float = config.POSITION_SIZE_PCT,
        stop_loss_pct: float = config.STOP_LOSS_PCT,
        exit_ma_window: int = config.EXIT_MA_WINDOW,
    ) -> None:
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.position_size_pct = position_size_pct
        self.stop_loss_pct = stop_loss_pct
        self.exit_ma_window = exit_ma_window

    # ── Sizing ────────────────────────────────────────────────────────────────

    def size_position(self, portfolio_value: float, n_open_positions: int) -> float:
        """
        Dollar amount to allocate to a new position.

        Returns 0 if:
          - Max positions already reached
          - Portfolio value < 10% of initial capital (capital preservation)
        """
        if n_open_positions >= self.max_positions:
            return 0.0
        if portfolio_value < self.initial_capital * 0.10:
            return 0.0
        return portfolio_value * self.position_size_pct

    # ── Exit conditions ───────────────────────────────────────────────────────

    def check_stop(self, entry_price: float, current_price: float) -> bool:
        """True if current price has breached the hard stop loss."""
        if entry_price <= 0:
            return False
        pnl_pct = (current_price - entry_price) / entry_price
        return pnl_pct <= self.stop_loss_pct

    def check_exit(self, entry_price: float, current_price: float, ma_20: float) -> bool:
        """
        True if take-profit triggered: price has reverted above the 20-day MA.
        This is the mean-reversion target exit.
        """
        if any(v <= 0 for v in [entry_price, current_price, ma_20]):
            return False
        return current_price > ma_20

    def stop_price(self, entry_price: float) -> float:
        """Exact price level at which stop loss triggers."""
        return entry_price * (1 + self.stop_loss_pct)

    # ── Portfolio exposure ────────────────────────────────────────────────────

    def portfolio_exposure(self, open_positions: dict, portfolio_value: float) -> float:
        """
        Fraction of portfolio currently deployed in open positions.
        open_positions: {ticker: {'shares': float, 'current_price': float, ...}}
        """
        if portfolio_value <= 0:
            return 0.0
        deployed = sum(
            pos.get("shares", 0) * pos.get("current_price", 0)
            for pos in open_positions.values()
        )
        return deployed / portfolio_value
