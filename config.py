# All tunable parameters live here. Never hardcode values elsewhere.

# ── Universe ──────────────────────────────────────────────────────────────────
UNIVERSE_SIZE = 25

# ── Data ──────────────────────────────────────────────────────────────────────
LOOKBACK_DAYS = 730          # 2 calendar years of daily data
DATA_CACHE_DIR = "data/cache"
CACHE_TTL_HOURS = 24

# ── Signal parameters ─────────────────────────────────────────────────────────
MOMENTUM_WINDOW = 20         # days for momentum return calculation
ENTRY_MA_WINDOW = 5          # short MA for pullback entry
EXIT_MA_WINDOW = 20          # mean-reversion target MA
VOLUME_MULTIPLIER = 1.2      # volume must exceed this × 20-day avg
MOMENTUM_PERCENTILE = 0.70   # top 30% of universe by momentum

# ── Risk & execution ──────────────────────────────────────────────────────────
STOP_LOSS_PCT = -0.08        # -8% hard stop from entry price
MAX_POSITIONS = 10           # maximum concurrent open positions
POSITION_SIZE_PCT = 0.10     # 10% of portfolio equity per position
INITIAL_CAPITAL = 100_000    # paper portfolio starting value (USD)
COMMISSION = 0.001           # 0.1% per side (realistic for small-cap)

# ── Reporting ─────────────────────────────────────────────────────────────────
RISK_FREE_RATE = 0.04        # annualised, for Sharpe calculation
BENCHMARK_TICKER = "SPY"

# ── Alpaca paper trading ───────────────────────────────────────────────────────
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
