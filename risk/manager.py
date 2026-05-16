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
        take_profit_pct: float = config.TAKE_PROFIT_PCT,
        trailing_activate_pct: float = config.TRAILING_STOP_ACTIVATE_PCT,
        trailing_trail_pct: float = config.TRAILING_STOP_TRAIL_PCT,
        hard_stop_dollar: float = config.HARD_STOP_DOLLAR,
    ) -> None:
        self.initial_capital       = initial_capital
        self.max_positions         = max_positions
        self.position_size_pct     = position_size_pct
        self.stop_loss_pct         = stop_loss_pct
        self.take_profit_pct       = take_profit_pct
        self.trailing_activate_pct = trailing_activate_pct
        self.trailing_trail_pct    = trailing_trail_pct
        self.hard_stop_dollar      = hard_stop_dollar

    # ── Sizing ────────────────────────────────────────────────────────────────

    def size_position(self, portfolio_value: float, n_open_positions: int) -> float:
        if n_open_positions >= self.max_positions:
            return 0.0
        if portfolio_value < self.initial_capital * 0.10:
            return 0.0
        return portfolio_value * self.position_size_pct

    # ── Exit conditions ───────────────────────────────────────────────────────

    def check_stop(self, entry_price: float, current_price: float) -> bool:
        """Hard stop loss at -6% from entry."""
        if entry_price <= 0:
            return False
        return (current_price - entry_price) / entry_price <= self.stop_loss_pct

    def check_take_profit(self, entry_price: float, current_price: float) -> bool:
        """Hard take profit at +15% from entry."""
        if entry_price <= 0:
            return False
        return (current_price - entry_price) / entry_price >= self.take_profit_pct

    def check_trailing_stop(
        self, entry_price: float, peak_price: float, current_price: float
    ) -> bool:
        """
        Trailing stop: activates once position is up >= 8% from entry.
        Once active, exit if price falls >= 4% below the running peak.
        """
        if entry_price <= 0 or peak_price <= 0:
            return False
        ever_up_enough = (peak_price - entry_price) / entry_price >= self.trailing_activate_pct
        if not ever_up_enough:
            return False
        return (peak_price - current_price) / peak_price >= self.trailing_trail_pct

    def check_hard_dollar_stop(
        self, entry_price: float, current_price: float, shares: float
    ) -> bool:
        """Hard dollar loss cap — fires if unrealised loss exceeds the threshold."""
        if entry_price <= 0 or shares <= 0:
            return False
        dollar_loss = shares * (entry_price - current_price)
        return dollar_loss >= self.hard_stop_dollar

    def stop_price(self, entry_price: float) -> float:
        return entry_price * (1 + self.stop_loss_pct)

    def trail_stop_price(self, peak_price: float) -> float:
        return peak_price * (1 - self.trailing_trail_pct)

    # ── Portfolio exposure ────────────────────────────────────────────────────

    def portfolio_exposure(self, open_positions: dict, portfolio_value: float) -> float:
        if portfolio_value <= 0:
            return 0.0
        deployed = sum(
            pos.get("shares", 0) * pos.get("current_price", 0)
            for pos in open_positions.values()
        )
        return deployed / portfolio_value
