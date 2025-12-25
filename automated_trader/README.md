# Automated Polymarket Trading Bot

A systematic, rule-based trading bot for Polymarket prediction markets implementing a mean-reversion strategy with strict risk management.

## Strategy Overview

**Objective**: Generate passive income through small probabilistic mispricings  
**Method**: Mean reversion with 7% edge requirement  
**Risk Profile**: Conservative position sizing with hard stops

## Key Features

- ✅ **Event-driven architecture** - Polls order books at configurable intervals
- ✅ **Strict market selection** - Volume filters and resolution date requirements
- ✅ **Fair value calculation** - Midpoint-based probability estimation
- ✅ **Position management** - Max 5 concurrent positions, 20% max deployment
- ✅ **Risk controls** - Daily loss caps, consecutive loss limits
- ✅ **Comprehensive logging** - Every trade logged with full context
- ✅ **Dry run mode** - Test strategy without executing real trades

## Strategy Rules

### Market Selection
- Binary Yes/No markets only
- Total volume >= $250,000
- 24h volume >= $25,000
- Resolution >= 7 days away
- Excludes breaking news markets

### Entry Logic
- **Buy YES** if: `best_yes_price <= fair_value - 0.07`
- **Buy NO** if: `best_no_price <= (1 - fair_value) - 0.07`

### Position Sizing
- Max 2% of bankroll per trade
- Max 20% total deployment
- Max 5 concurrent positions
- No averaging down

### Exit Rules
- **Profit target**: Entry + 5%
- **Stop loss**: Entry - 10%
- **Timeout**: 72 hours
- Never hold through resolution

### Risk Management
- Stop after 3 consecutive losses
- Daily loss cap: 2% of bankroll
- Automatic daily reset

## Installation

```bash
cd automated_trader
pip install -r requirements.txt
```

## Configuration

Edit `config.py` to adjust strategy parameters:

```python
# Market selection
MIN_TOTAL_VOLUME = 250_000
MIN_24H_VOLUME = 25_000
MIN_DAYS_TO_RESOLUTION = 7

# Entry/Exit
EDGE_REQUIRED = 0.07         # 7% edge
PROFIT_TARGET = 0.05         # 5% profit
STOP_LOSS_PCT = -0.10        # 10% stop

# Position sizing
MAX_POSITION_SIZE_PCT = 0.02 # 2% per trade
MAX_DEPLOYED_PCT = 0.20      # 20% max deployed
MAX_CONCURRENT_POSITIONS = 5

# Risk
MAX_CONSECUTIVE_LOSSES = 3
DAILY_MAX_LOSS_PCT = 0.02    # 2% daily cap

# Execution
ORDER_BOOK_POLL_SECONDS = 30
DRY_RUN_MODE = True          # Set False for live trading
```

## Usage

### Dry Run (Recommended First)

```bash
python automated_trader/trader.py
```

This will:
- Scan markets
- Generate signals
- Simulate trades
- Log all activity
- NOT execute real orders

### Live Trading

1. Update `config.py`:
   ```python
   DRY_RUN_MODE = False
   INITIAL_BANKROLL = 100.0  # Your actual balance
   ```

2. Ensure Polymarket credentials are configured

3. Run:
   ```bash
   python automated_trader/trader.py
   ```

## Monitoring

### Real-time Logs

The bot outputs detailed logs:
```
📊 ITERATION 1 - 2025-12-24 19:45:00
🔍 Scanning for trading opportunities...
✓ Found 12 tradeable markets
💡 Opportunity #1: Will Trump win 2024?
📈 ENTRY SIGNAL
   Signal: BUY_YES
   Entry: $0.650
   Target: $0.700 (+5.0%)
   Stop: $0.585 (-10.0%)
   Size: $2.00
   ⚠️ DRY RUN - No actual trade executed
```

### Trade Logs

All trades logged to `automated_trader/logs/trades.jsonl`:

```json
{"event": "ENTRY", "timestamp": "2025-12-24T19:45:00", "market_question": "Will Trump win 2024?", "signal": "BUY_YES", "entry_price": 0.65, "position_size": 2.0, "reason": "YES edge: 0.08 >= 0.07"}
{"event": "EXIT", "timestamp": "2025-12-24T21:30:00", "market_question": "Will Trump win 2024?", "exit_price": 0.70, "pnl": 0.15, "pnl_pct": 7.5, "exit_reason": "Profit target hit"}
```

### Performance Stats

Check performance:
```python
from automated_trader.trade_logger import TradeLogger

logger = TradeLogger()
stats = logger.get_performance_stats()
print(f"Win Rate: {stats['win_rate']:.1f}%")
print(f"Total P&L: ${stats['total_pnl']:.2f}")
```

## Architecture

```
automated_trader/
├── config.py              # All strategy parameters
├── market_selector.py     # Market filtering
├── signal_generator.py    # Entry/exit signals
├── position_manager.py    # Position tracking
├── risk_controller.py     # Risk management
├── trade_logger.py        # Trade logging
├── trader.py             # Main event loop
└── logs/
    └── trades.jsonl      # Trade history
```

## Fail-Safes

- API errors handled with retries
- Missing data skipped gracefully
- Positions tracked independently
- Automatic daily resets
- Manual shutdown preserves state

## Testing

Run dry run for 24+ hours to verify:
- Market selection works correctly
- Signals generate as expected
- Risk limits are enforced
- Logging captures all events

## Important Notes

⚠️ **This is a trading bot that will execute real trades when `DRY_RUN_MODE = False`**

- Always test in dry run mode first
- Start with small bankroll
- Monitor closely initially
- Understand all rules before going live
- No guarantees of profitability

## Customization

All strategy parameters are in `config.py` - adjust as needed:
- Tighten/loosen edge requirements
- Increase/decrease position sizes
- Modify risk limits
- Change polling intervals

## Support

For issues or questions, review the code comments - every module is extensively documented.
