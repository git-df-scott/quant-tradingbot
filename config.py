# All tunable parameters live here. Never hardcode values elsewhere.

# ── Universe ──────────────────────────────────────────────────────────────────
UNIVERSE_SIZE = 25

# ── Data ──────────────────────────────────────────────────────────────────────
LOOKBACK_DAYS = 1600         # ~4.4 years so date-range backtests cover full 2022
DATA_CACHE_DIR = "data/cache"
CACHE_TTL_HOURS = 24

# ── Signal parameters ─────────────────────────────────────────────────────────
MOMENTUM_WINDOW = 20         # days for momentum return calculation
ENTRY_MA_WINDOW = 5          # short MA for pullback entry
EXIT_MA_WINDOW = 20          # mean-reversion target MA
VOLUME_MULTIPLIER = 1.2      # volume must exceed this × 20-day avg
MOMENTUM_PERCENTILE = 0.70   # top 30% of universe by momentum

# ── Risk & execution ──────────────────────────────────────────────────────────
STOP_LOSS_PCT = -0.06            # -6% hard stop
TAKE_PROFIT_PCT = 0.15           # +15% hard take profit
TRAILING_STOP_ACTIVATE_PCT = 0.08  # activate trailing stop once up 8%
TRAILING_STOP_TRAIL_PCT = 0.04   # trail 4% below running peak
HARD_STOP_DOLLAR = 1_000.0       # hard per-trade dollar loss cap
COOLDOWN_BARS = 10               # bars a ticker is banned after a stop-loss exit
MIN_BARS_BEFORE_ENTRY = 60       # skip entry if ticker has < 60 bars of history
MAX_POSITIONS = 10               # maximum concurrent open positions
POSITION_SIZE_PCT = 0.10         # 10% of portfolio equity per position
INITIAL_CAPITAL = 100_000        # paper portfolio starting value (USD)
COMMISSION = 0.001               # 0.1% per side (realistic for small-cap)
SLIPPAGE = 0.00075               # 0.075% per side (0.15% round trip)

# ── Reporting ─────────────────────────────────────────────────────────────────
RISK_FREE_RATE = 0.04        # annualised, for Sharpe calculation
BENCHMARK_TICKER = "SPY"

# ── Alpaca paper trading ───────────────────────────────────────────────────────
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
