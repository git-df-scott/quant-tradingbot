# All tunable parameters live here. Never hardcode values elsewhere.

# ── Universe ──────────────────────────────────────────────────────────────────
UNIVERSE_SIZE = 300
MIN_PRICE = 5.0          # skip stocks below $5 (penny stocks)
MAX_PRICE = 200.0        # skip stocks above $200 (mega-caps)
MIN_ADV = 300_000        # minimum 60-day average daily volume (shares)
MAX_DOWNLOAD_WORKERS = 10  # parallel threads for yfinance downloads

# ── Data ──────────────────────────────────────────────────────────────────────
LOOKBACK_DAYS = 1600         # default rolling window; server extends this dynamically for historical backtests
DATA_CACHE_DIR = "data/cache"
CACHE_TTL_HOURS = 24

# ── Signal parameters ─────────────────────────────────────────────────────────
MOMENTUM_WINDOW = 20         # days for momentum return calculation
ENTRY_MA_WINDOW = 5          # short MA for pullback entry
EXIT_MA_WINDOW = 20          # mean-reversion target MA
VOLUME_MULTIPLIER = 1.2      # volume must exceed this × 20-day avg
MOMENTUM_PERCENTILE = 0.70   # top 30% of universe by momentum

# ── Risk & execution ──────────────────────────────────────────────────────────
STOP_LOSS_PCT = -0.06            # -6% hard stop (was -8%)
TAKE_PROFIT_PCT = 0.15           # +15% hard take profit; replaces MA20 exit
TRAILING_STOP_ACTIVATE_PCT = 0.08  # activate trailing stop once up 8%
TRAILING_STOP_TRAIL_PCT = 0.04   # trail 4% below running peak
HARD_STOP_DOLLAR = 1_000.0       # hard per-trade dollar loss cap
COOLDOWN_BARS = 10               # bars a ticker is banned after a stop-loss exit
MIN_BARS_BEFORE_ENTRY = 60       # skip entry if ticker has < 60 bars of history
MAX_POSITIONS = 5                # maximum concurrent open positions
POSITION_SIZE_PCT = 0.10         # 10% of portfolio equity per position
INITIAL_CAPITAL = 100_000        # paper portfolio starting value (USD)
COMMISSION = 0.001               # 0.1% per side (realistic for small-cap)

# ── Reporting ─────────────────────────────────────────────────────────────────
RISK_FREE_RATE = 0.04        # annualised, for Sharpe calculation
BENCHMARK_TICKER = "SPY"

# ── Market regime filter (SPY SMA-based) ──────────────────────────────────────
REGIME_SMA_FAST = 50          # SMA period for death-cross detection
REGIME_SMA_SLOW = 200         # Primary trend SMA; price below = caution
REGIME_CAUTION_SIZE_MULT = 0.60            # position $ multiplier in caution (−40% vs bull)
REGIME_CAUTION_MAX_POSITIONS = 5           # max concurrent positions in caution mode
REGIME_CAUTION_MOMENTUM_PERCENTILE = 0.95  # top 5% only in caution (was 15%)
REGIME_CAUTION_VOLUME_MULTIPLIER = 2.0     # 2× avg volume required in caution (vs 1.2× in bull)

# ── Alpaca paper trading ───────────────────────────────────────────────────────
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
