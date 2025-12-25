"""
Configuration for Automated Polymarket Trading Bot
All strategy parameters defined as variables - do not hardcode in logic
"""

# ============================================================================
# MARKET SELECTION CRITERIA
# ============================================================================
MIN_TOTAL_VOLUME = 50_000       # Minimum total market volume in USD
MIN_24H_VOLUME = 250            # Minimum 24-hour volume in USD
MIN_HOURS_TO_RESOLUTION = 168   # Minimum hours until market closes (168 = 7 days)
BINARY_ONLY = True              # Only trade binary Yes/No markets

# Markets to exclude (breaking news, fast-moving)
EXCLUDED_KEYWORDS = [
    "breaking", "just announced", "live", "now", "urgent",
    "today", "tomorrow", "this week"
]

# Market health gate
MAX_BID_ASK_SPREAD_PCT = 0.08   # Skip if spread > 8%

# ============================================================================
# FAIR VALUE & ENTRY LOGIC
# ============================================================================
EDGE_REQUIRED = 0.07            # Required edge over fair value (7%)
PROFIT_TARGET = 0.05            # Target profit per trade (5%)
STOP_LOSS_PCT = -0.10           # Hard stop loss (-10%)

# ============================================================================
# POSITION SIZING
# ============================================================================
MAX_BET_SIZE = 10.0             # Maximum bet size in USD ($10)
DEFAULT_BET_SIZE = 5.0          # Default recommended bet size ($5)
MAX_POSITION_SIZE_PCT = 0.10    # Max 10% of bankroll per trade
MAX_DEPLOYED_PCT = 0.10         # Max 10% of bankroll deployed (1 position)
MAX_CONCURRENT_POSITIONS = 1    # Max 1 open position at a time
ALLOW_AVERAGING_DOWN = False    # Never average down into positions

# ============================================================================
# EXIT RULES
# ============================================================================
POSITION_TIMEOUT_HOURS = 72     # Exit if not filled after 72 hours
NEVER_HOLD_THROUGH_RESOLUTION = True  # Always exit before resolution

# ============================================================================
# RISK MANAGEMENT
# ============================================================================
MAX_CONSECUTIVE_LOSSES = 2      # Stop trading after 2 consecutive losses
WEEKLY_MAX_LOSS = 15.0          # Weekly loss cap in USD ($15)
DAILY_MAX_LOSS_PCT = 0.15       # Daily loss cap (15% of $100 bankroll)
RESET_LOSS_COUNTER_DAILY = True # Reset consecutive losses each day

# ============================================================================
# EXECUTION SETTINGS
# ============================================================================
ORDER_BOOK_POLL_SECONDS = 15    # How often to check order books
MAX_PARTIAL_FILL_WAIT_MINUTES = 10  # Wait time for partial fills
API_RETRY_ATTEMPTS = 3          # Retries for API errors
API_RETRY_DELAY_SECONDS = 5     # Delay between retries

# ============================================================================
# LOGGING
# ============================================================================
LOG_EVERY_TRADE = True          # Log all trades
LOG_FILE_PATH = "automated_trader/logs/trades.jsonl"
LOG_LEVEL = "INFO"              # DEBUG, INFO, WARNING, ERROR

# ============================================================================
# INITIAL SETTINGS
# ============================================================================
INITIAL_BANKROLL = 100.0        # Fixed weekly budget: $100
WEEKLY_BUDGET = 100.0           # Weekly budget allocation
DRY_RUN_MODE = True             # Set False ONLY after dry-run confirms compliance
