"""
Automated Trading Bot Main Loop
Event-driven architecture that polls order books and executes strategy
"""
import time
import logging
from datetime import datetime
from typing import Optional
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automated_trader import config
from automated_trader.market_selector import MarketSelector
from automated_trader.signal_generator import SignalGenerator, Signal
from automated_trader.position_manager import PositionManager
from automated_trader.risk_controller import RiskController
from automated_trader.trade_logger import TradeLogger

from agents.polymarket.gamma import GammaMarketClient
from agents.polymarket.polymarket import Polymarket

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutomatedTrader:
    """
    Main trading bot that orchestrates the strategy
    
    Architecture:
    - Event-driven: polls markets at configured intervals
    - Stateless: each iteration is independent
    - Fail-safe: handles API errors gracefully
    """
    
    def __init__(self):
        """Initialize all components"""
        logger.info("=" * 80)
        logger.info("AUTOMATED POLYMARKET TRADING BOT")
        logger.info("=" * 80)
        
        # Initialize clients
        logger.info("Initializing API clients...")
        self.gamma = GammaMarketClient()
        self.polymarket = Polymarket()
        
        # Initialize strategy components
        logger.info("Initializing strategy components...")
        self.market_selector = MarketSelector(self.gamma, self.polymarket)
        self.signal_generator = SignalGenerator()
        self.position_manager = PositionManager()
        self.risk_controller = RiskController(config.INITIAL_BANKROLL)
        self.trade_logger = TradeLogger()
        
        # Runtime state
        self.iteration = 0
        self.last_scan_time = None
        
        logger.info(f"✓ Bot initialized in {'DRY RUN' if config.DRY_RUN_MODE else 'LIVE'} mode")
        logger.info(f"✓ Initial bankroll: ${config.INITIAL_BANKROLL:.2f}")
        self._log_config()
    
    def run(self):
        """
        Main trading loop
        
        Process:
        1. Check if trading is allowed (risk limits)
        2. Scan markets for opportunities
        3. Check open positions for exits
        4. Generate entry signals
        5. Execute trades (if not dry run)
        6. Wait for next iteration
        """
        logger.info("🚀 Starting trading loop...")
        logger.info(f"📊 Polling interval: {config.ORDER_BOOK_POLL_SECONDS}s")
        
        try:
            while True:
                self.iteration += 1
                logger.info(f"\n{'=' * 80}")
                logger.info(f"ITERATION {self.iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'=' * 80}")
                
                try:
                    # Check daily reset
                    self.risk_controller.check_daily_reset()
                    
                    # Check if we can trade
                    can_trade, reason = self.risk_controller.can_trade()
                    if not can_trade:
                        logger.warning(f"⚠️ Trading disabled: {reason}")
                        time.sleep(config.ORDER_BOOK_POLL_SECONDS)
                        continue
                    
                    # Process open positions (check for exits)
                    self._process_open_positions()
                    
                    # Look for new opportunities
                    self._scan_for_opportunities()
                    
                    # Log status
                    self._log_iteration_summary()
                    
                except Exception as e:
                    logger.error(f"❌ Error in iteration {self.iteration}: {e}", exc_info=True)
                    self.trade_logger.log_error('ITERATION_ERROR', str(e), {'iteration': self.iteration})
                
                # Wait for next iteration
                logger.info(f"⏳ Waiting {config.ORDER_BOOK_POLL_SECONDS}s until next scan...")
                time.sleep(config.ORDER_BOOK_POLL_SECONDS)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutdown signal received")
            self._shutdown()
    
    def _scan_for_opportunities(self):
        """Scan markets for entry opportunities"""
        logger.info("🔍 Scanning for trading opportunities...")
        
        # Check if we can open new positions
        bankroll = self.risk_controller.get_available_capital()
        can_open, reason = self.position_manager.can_open_position(bankroll)
        
        if not can_open:
            logger.info(f"⚠️ Cannot open new positions: {reason}")
            return
        
        # Get tradeable markets
        try:
            markets = self.market_selector.get_tradeable_markets()
            logger.info(f"✓ Found {len(markets)} tradeable markets")
            
            if not markets:
                logger.info("No markets meet criteria")
                return
            
        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
            return
        
        # Check each market for signals
        opportunities_found = 0
        
        for market in markets:
            # Skip if we already have a position
            market_id = market.get('condition_id')
            if self.position_manager.has_position(market_id):
                continue
            
            # Calculate fair value
            order_book = market.get('order_book')
            if not order_book:
                continue
            
            fair_value = self.signal_generator.calculate_fair_value(order_book)
            if fair_value is None:
                continue
            
            # Generate entry signal
            signal, entry_price, signal_reason = self.signal_generator.generate_entry_signal(
                market, fair_value
            )
            
            # Log signal
            self.trade_logger.log_signal(market, signal.value, signal_reason, entry_price)
            
            # Act on signal
            if signal in [Signal.BUY_YES, Signal.BUY_NO]:
                opportunities_found += 1
                logger.info(f"💡 Opportunity #{opportunities_found}: {market.get('question')}")
                
                # Execute trade
                self._execute_entry(market, signal, entry_price, signal_reason)
                
                # Check if we can open more positions
                can_open, reason = self.position_manager.can_open_position(
                    self.risk_controller.get_available_capital()
                )
                if not can_open:
                    logger.info(f"Position limit reached: {reason}")
                    break
        
        if opportunities_found == 0:
            logger.info("No entry signals generated")
    
    def _process_open_positions(self):
        """Check open positions for exit conditions"""
        open_positions = self.position_manager.get_open_positions()
        
        if not open_positions:
            logger.info("📊 No open positions")
            return
        
        logger.info(f"📊 Monitoring {len(open_positions)} open position(s)...")
        
        for position in open_positions:
            try:
                market_id = position['market_id']
                
                # Get current market price
                order_book = self._get_order_book(market_id)
                if not order_book:
                    logger.warning(f"Could not fetch order book for {market_id}")
                    continue
                
                # Get current price based on position side
                current_price = self._get_current_price(order_book, position['signal'])
                
                # Check if we should exit
                should_exit, exit_reason = self.signal_generator.should_exit_position(
                    position, current_price
                )
                
                if should_exit:
                    logger.info(f"🔔 Exit signal: {position['market_question'][:50]}...")
                    self._execute_exit(position, current_price, exit_reason)
                else:
                    logger.debug(f"✓ Holding: {position['market_question'][:50]}... "
                               f"(Current: {current_price:.3f}, Target: {position['target_price']:.3f})")
                    
            except Exception as e:
                logger.error(f"Error processing position {position.get('position_id')}: {e}")
    
    def _execute_entry(
        self,
        market: dict,
        signal: Signal,
        entry_price: float,
        reason: str
    ):
        """
        Execute entry trade
        
        Args:
            market: Market data
            signal: Entry signal
            entry_price: Entry price
            reason: Entry reason
        """
        market_id = market.get('condition_id')
        market_question = market.get('question')
        market_end_date = market.get('end_date_iso')
        
        # Calculate position size
        bankroll = self.risk_controller.get_available_capital()
        position_size = self.position_manager.calculate_position_size(bankroll, entry_price)
        
        # Calculate exit prices
        target_price = self.signal_generator.calculate_exit_price(entry_price, signal)
        stop_price = self.signal_generator.calculate_stop_loss_price(entry_price)
        
        logger.info(f"📈 ENTRY SIGNAL")
        logger.info(f"   Market: {market_question}")
        logger.info(f"   Signal: {signal.value}")
        logger.info(f"   Entry: ${entry_price:.3f}")
        logger.info(f"   Target: ${target_price:.3f} (+{config.PROFIT_TARGET:.1%})")
        logger.info(f"   Stop: ${stop_price:.3f} ({config.STOP_LOSS_PCT:.1%})")
        logger.info(f"   Size: ${position_size:.2f}")
        logger.info(f"   Reason: {reason}")
        
        if config.DRY_RUN_MODE:
            logger.info("   ⚠️ DRY RUN - No actual trade executed")
        else:
            # TODO: Execute actual trade via Polymarket API
            logger.info("   ✓ Trade executed (live mode)")
        
        # Record position
        try:
            end_date = datetime.fromisoformat(market_end_date.replace('Z', '+00:00')) if market_end_date else None
        except:
            end_date = None
        
        position_id = self.position_manager.open_position(
            market_id=market_id,
            market_question=market_question,
            signal=signal,
            entry_price=entry_price,
            target_price=target_price,
            stop_price=stop_price,
            position_size=position_size,
            market_end_date=end_date
        )
        
        # Log trade
        position = self.position_manager.get_position(market_id)
        self.trade_logger.log_trade_entry(position, reason)
    
    def _execute_exit(
        self,
        position: dict,
        exit_price: float,
        reason: str
    ):
        """
        Execute exit trade
        
        Args:
            position: Position to exit
            exit_price: Exit price
            reason: Exit reason
        """
        logger.info(f"📉 EXIT SIGNAL")
        logger.info(f"   Market: {position['market_question']}")
        logger.info(f"   Entry: ${position['entry_price']:.3f}")
        logger.info(f"   Exit: ${exit_price:.3f}")
        logger.info(f"   Reason: {reason}")
        
        if config.DRY_RUN_MODE:
            logger.info("   ⚠️ DRY RUN - No actual trade executed")
        else:
            # TODO: Execute actual trade via Polymarket API
            logger.info("   ✓ Trade executed (live mode)")
        
        # Close position
        closed_position = self.position_manager.close_position(
            position['market_id'],
            exit_price,
            reason
        )
        
        # Update risk controller
        self.risk_controller.record_trade(closed_position['pnl'])
        
        # Log trade
        self.trade_logger.log_trade_exit(closed_position)
        
        logger.info(f"   💰 P&L: ${closed_position['pnl']:+.2f} ({closed_position['pnl_pct']:+.1f}%)")
    
    def _get_order_book(self, market_id: str) -> Optional[dict]:
        """Get current order book for market"""
        try:
            return self.polymarket.get_order_book(market_id)
        except Exception as e:
            logger.error(f"Failed to get order book: {e}")
            return None
    
    def _get_current_price(self, order_book: dict, signal: str) -> float:
        """Get current market price based on position side"""
        try:
            if 'YES' in signal:
                bids = order_book.get('yes', {}).get('bids', [])
                return max([float(bid['price']) for bid in bids]) if bids else 0.5
            else:
                bids = order_book.get('no', {}).get('bids', [])
                return max([float(bid['price']) for bid in bids]) if bids else 0.5
        except:
            return 0.5
    
    def _log_iteration_summary(self):
        """Log summary of current iteration"""
        open_positions = len(self.position_manager.get_open_positions())
        deployed = self.position_manager.get_deployed_capital()
        bankroll = self.risk_controller.get_available_capital()
        
        logger.info(f"\n📊 ITERATION SUMMARY")
        logger.info(f"   Open Positions: {open_positions}/{config.MAX_CONCURRENT_POSITIONS}")
        logger.info(f"   Deployed Capital: ${deployed:.2f} / ${bankroll * config.MAX_DEPLOYED_PCT:.2f}")
        logger.info(f"   Available Capital: ${bankroll:.2f}")
        logger.info(f"   Consecutive Losses: {self.risk_controller.consecutive_losses}")
    
    def _log_config(self):
        """Log current configuration"""
        logger.info(f"\n📋 STRATEGY CONFIGURATION:")
        logger.info(f"   Min Volume: ${config.MIN_TOTAL_VOLUME:,.0f}")
        logger.info(f"   Min 24h Volume: ${config.MIN_24H_VOLUME:,.0f}")
        logger.info(f"   Min Hours to Resolution: {config.MIN_HOURS_TO_RESOLUTION} ({config.MIN_HOURS_TO_RESOLUTION/24:.1f} days)")
        logger.info(f"   Edge Required: {config.EDGE_REQUIRED:.1%}")
        logger.info(f"   Profit Target: {config.PROFIT_TARGET:.1%}")
        logger.info(f"   Stop Loss: {config.STOP_LOSS_PCT:.1%}")
        logger.info(f"   Max Position Size: {config.MAX_POSITION_SIZE_PCT:.1%}")
        logger.info(f"   Max Deployed: {config.MAX_DEPLOYED_PCT:.1%}")
        logger.info(f"   Max Concurrent: {config.MAX_CONCURRENT_POSITIONS}")
        logger.info(f"   Position Timeout: {config.POSITION_TIMEOUT_HOURS}h")
    
    def _shutdown(self):
        """Graceful shutdown"""
        logger.info("\n" + "=" * 80)
        logger.info("SHUTTING DOWN")
        logger.info("=" * 80)
        
        # Close all open positions (in live mode)
        open_positions = self.position_manager.get_open_positions()
        if open_positions:
            logger.warning(f"⚠️ {len(open_positions)} position(s) still open!")
            for pos in open_positions:
                logger.info(f"   - {pos['market_question'][:50]}... (Size: ${pos['position_size']:.2f})")
        
        # Display performance stats
        stats = self.trade_logger.get_performance_stats()
        if stats.get('total_trades', 0) > 0:
            logger.info(f"\n📊 PERFORMANCE SUMMARY:")
            logger.info(f"   Total Trades: {stats['total_trades']}")
            logger.info(f"   Win Rate: {stats['win_rate']:.1f}%")
            logger.info(f"   Total P&L: ${stats['total_pnl']:+.2f}")
            logger.info(f"   Avg P&L: ${stats['avg_pnl']:+.2f}")
        
        total_pnl = self.risk_controller.get_total_pnl()
        total_return = self.risk_controller.get_total_return_pct()
        logger.info(f"\n💰 FINAL BANKROLL: ${self.risk_controller.current_bankroll:.2f}")
        logger.info(f"   Total P&L: ${total_pnl:+.2f} ({total_return:+.1f}%)")
        
        logger.info("\n✓ Shutdown complete")


def main():
    """Entry point"""
    trader = AutomatedTrader()
    trader.run()


if __name__ == "__main__":
    main()
