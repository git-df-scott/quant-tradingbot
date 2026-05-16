"""
Alpaca paper trading integration.
If API keys are missing/blank, falls back to MarketSimulator automatically.
Interface mirrors MarketSimulator exactly.
"""

from __future__ import annotations

import os
import time
from functools import wraps

from dotenv import load_dotenv

import config

load_dotenv()

_API_KEY    = os.getenv("ALPACA_API_KEY", "").strip()
_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "").strip()
_BASE_URL   = os.getenv("ALPACA_BASE_URL", config.ALPACA_BASE_URL)


def _retry(max_attempts: int = 3, base_delay: float = 1.0):
    """Exponential backoff decorator for API calls."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(base_delay * (2 ** attempt))
                    print(f"[paper_trader] Retry {attempt + 1}/{max_attempts}: {exc}")
        return wrapper
    return decorator


class _SimFallback:
    """Thin wrapper that imports and exposes MarketSimulator under PaperTrader's interface."""
    def __init__(self) -> None:
        from simulation.market_sim import MarketSimulator
        self._sim = MarketSimulator()

    def get_price(self, ticker: str) -> dict | None:
        return self._sim.get_price(ticker)

    def submit_order(self, ticker: str, qty: float, side: str):
        return self._sim.submit_order(ticker, qty, side)

    def get_portfolio(self) -> dict:
        return self._sim.get_portfolio()

    def reset(self) -> None:
        self._sim.reset()

    def step(self) -> None:
        self._sim.step()


class PaperTrader:
    """
    Wraps Alpaca paper trading API.
    Automatically falls back to MarketSimulator when API keys are not configured.

    Methods mirror MarketSimulator:
        get_price(ticker)
        submit_order(ticker, qty, side)
        get_portfolio()
        reset()
    """

    def __init__(self) -> None:
        if not _API_KEY or not _SECRET_KEY:
            print("No API keys found — running in simulation mode.")
            self._backend = _SimFallback()
            self._live = False
        else:
            try:
                import alpaca_trade_api as tradeapi
                self._api  = tradeapi.REST(_API_KEY, _SECRET_KEY, _BASE_URL)
                self._api.get_account()   # validate keys
                self._backend = None
                self._live = True
                print(f"Connected to Alpaca paper trading at {_BASE_URL}.")
            except Exception as exc:
                print(f"Alpaca connection failed ({exc}) — falling back to simulation mode.")
                self._backend = _SimFallback()
                self._live = False

    # ── Unified interface ─────────────────────────────────────────────────────

    @_retry()
    def get_price(self, ticker: str) -> dict | None:
        if not self._live:
            return self._backend.get_price(ticker)

        from alpaca_trade_api.rest import TimeFrame
        import pandas as pd

        try:
            bars = self._api.get_bars(ticker, TimeFrame.Day, limit=1).df
            if bars.empty:
                return None
            row = bars.iloc[-1]
            return {
                "open":  row["open"],
                "close": row["close"],
                "date":  bars.index[-1],
            }
        except Exception as exc:
            print(f"[paper_trader] get_price({ticker}) failed: {exc}")
            return None

    @_retry()
    def submit_order(self, ticker: str, qty: float, side: str):
        if not self._live:
            return self._backend.submit_order(ticker, qty, side)

        try:
            order = self._api.submit_order(
                symbol=ticker,
                qty=qty,
                side=side,
                type="market",
                time_in_force="day",
            )
            return order
        except Exception as exc:
            msg = str(exc)
            if "insufficient" in msg.lower():
                print(f"[paper_trader] Insufficient buying power for {ticker} — skipped.")
            elif "not found" in msg.lower() or "invalid" in msg.lower():
                print(f"[paper_trader] Invalid ticker {ticker} — skipped.")
            else:
                print(f"[paper_trader] submit_order({ticker}) failed: {exc}")
            return None

    @_retry()
    def get_portfolio(self) -> dict:
        if not self._live:
            return self._backend.get_portfolio()

        account   = self._api.get_account()
        positions = self._api.list_positions()

        pos_detail = {
            p.symbol: {
                "shares":    float(p.qty),
                "price":     float(p.current_price),
                "mkt_value": float(p.market_value),
            }
            for p in positions
        }

        return {
            "cash":      float(account.cash),
            "equity":    float(account.equity),
            "positions": pos_detail,
        }

    def reset(self) -> None:
        if not self._live:
            self._backend.reset()
            return

        # Cancel all open orders and liquidate all positions
        self._api.cancel_all_orders()
        self._api.close_all_positions()
        print("Alpaca paper account reset: all orders cancelled, all positions liquidated.")
