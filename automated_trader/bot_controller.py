"""
Bot Controller - Manages the automated trading bot lifecycle
"""
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

from automated_trader.market_selector import MarketSelector
from automated_trader.signal_generator import SignalGenerator
from automated_trader.position_manager import PositionManager
from automated_trader.risk_controller import RiskController
from automated_trader.trade_logger import TradeLogger
from automated_trader import config

logger = logging.getLogger(__name__)


class BotController:
    """Controls the automated trading bot with start/stop capability"""
    
    def __init__(self, gamma_client, polymarket_client):
        self.gamma = gamma_client
        self.polymarket = polymarket_client
        
        # Strategy components
        self.market_selector = MarketSelector(self.gamma, self.polymarket)
        self.signal_generator = SignalGenerator()
        self.position_manager = PositionManager()
        self.risk_controller = RiskController(config.INITIAL_BANKROLL)
        self.trade_logger = TradeLogger()
        
        # Bot state
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.iteration = 0
        self.last_scan_time: Optional[datetime] = None
        self.status_message = "Idle"
        self.logs: List[str] = []
        
    def start(self):
        """Start the bot in a background thread"""
        if self.is_running:
            return False, "Bot is already running"
        
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        self._add_log("🚀 Bot started")
        return True, "Bot started successfully"
    
    def stop(self):
        """Stop the bot"""
        if not self.is_running:
            return False, "Bot is not running"
        
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        self._add_log("🛑 Bot stopped")
        return True, "Bot stopped successfully"
    
    def _run_loop(self):
        """Main bot loop (runs in background thread)"""
        while self.is_running:
            try:
                self.iteration += 1
                self._add_log(f"\n{'='*60}")
                self._add_log(f"ITERATION {self.iteration} - {datetime.now().strftime('%H:%M:%S')}")
                
                # Check risk limits
                can_trade, reason = self.risk_controller.can_trade()
                if not can_trade:
                    self.status_message = f"Halted: {reason}"
                    self._add_log(f"⚠️ {self.status_message}")
                    time.sleep(config.ORDER_BOOK_POLL_SECONDS)
                    continue
                
                # Check daily reset
                self.risk_controller.check_daily_reset()
                
                # Process open positions
                self._process_positions()
                
                # Scan for new opportunities
                self._scan_markets()
                
                self.last_scan_time = datetime.now()
                self.status_message = "Scanning for opportunities..."
                
                # Wait for next iteration
                time.sleep(config.ORDER_BOOK_POLL_SECONDS)
                
            except Exception as e:
                self._add_log(f"❌ Error: {str(e)}")
                logger.error(f"Bot error: {e}", exc_info=True)
                time.sleep(config.ORDER_BOOK_POLL_SECONDS)
    
    def _scan_markets(self):
        """Scan markets for entry opportunities"""
        try:
            # Check if we can open positions
            bankroll = self.risk_controller.get_available_capital()
            can_open, reason = self.position_manager.can_open_position(bankroll)
            
            if not can_open:
                self._add_log(f"⚠️ {reason}")
                return
            
            # Get tradeable markets
            markets = self.market_selector.get_tradeable_markets()
            self._add_log(f"📊 Found {len(markets)} tradeable markets")
            
            if not markets:
                self._add_log("⚠️ No markets meet criteria (volume, spread, resolution time)")
                return
            
            # Check each market for signals
            for idx, market in enumerate(markets, 1):
                if not self.is_running:
                    break
                
                market_id = market.get('condition_id')
                market_question = market.get('question', 'Unknown')[:60]
                
                if self.position_manager.has_position(market_id):
                    continue
                
                self._add_log(f"\n🔍 Analyzing Market {idx}/{len(markets)}:")
                self._add_log(f"   {market_question}...")
                
                # Calculate fair value and generate signal
                order_book = market.get('order_book')
                if not order_book:
                    self._add_log("   ⚠️ No order book data")
                    continue
                
                fair_value = self.signal_generator.calculate_fair_value(order_book)
                if fair_value is None:
                    self._add_log("   ⚠️ Cannot calculate fair value")
                    continue
                
                # Get current prices for display
                yes_asks = order_book.get('yes', {}).get('asks', [])
                no_asks = order_book.get('no', {}).get('asks', [])
                best_yes = min([float(a['price']) for a in yes_asks]) if yes_asks else None
                best_no = min([float(a['price']) for a in no_asks]) if no_asks else None
                
                self._add_log(f"   Fair Value: {fair_value:.1%}")
                self._add_log(f"   YES Price: ${best_yes:.3f} | NO Price: ${best_no:.3f}")
                
                signal, entry_price, signal_reason = self.signal_generator.generate_entry_signal(
                    market, fair_value
                )
                
                if signal.value in ['BUY_YES', 'BUY_NO']:
                    self._add_log(f"   ✅ SIGNAL: {signal_reason}")
                    self._execute_entry(market, signal, entry_price, signal_reason)
                    
                    # Check if we can open more
                    can_open, _ = self.position_manager.can_open_position(
                        self.risk_controller.get_available_capital()
                    )
                    if not can_open:
                        break
                else:
                    self._add_log(f"   ❌ {signal_reason}")
                        
        except Exception as e:
            self._add_log(f"❌ Scan error: {str(e)}")
    
    def _process_positions(self):
        """Check open positions for exits"""
        open_positions = self.position_manager.get_open_positions()
        
        if not open_positions:
            return
        
        self._add_log(f"📈 Monitoring {len(open_positions)} position(s)")
        
        for position in open_positions:
            try:
                market_id = position['market_id']
                
                # Get current price
                order_book = self._get_order_book(market_id)
                if not order_book:
                    continue
                
                current_price = self._get_current_price(order_book, position['signal'])
                
                # Check for exit
                should_exit, exit_reason = self.signal_generator.should_exit_position(
                    position, current_price
                )
                
                if should_exit:
                    self._execute_exit(position, current_price, exit_reason)
                    
            except Exception as e:
                self._add_log(f"❌ Position error: {str(e)}")
    
    def _execute_entry(self, market, signal, entry_price, reason):
        """Execute entry trade"""
        market_id = market.get('condition_id')
        market_question = market.get('question')
        
        bankroll = self.risk_controller.get_available_capital()
        position_size = self.position_manager.calculate_position_size(bankroll, entry_price)
        
        target_price = self.signal_generator.calculate_exit_price(entry_price, signal)
        stop_price = self.signal_generator.calculate_stop_loss_price(entry_price)
        
        self._add_log(f"📈 ENTRY: {market_question[:50]}...")
        self._add_log(f"   {signal.value} @ ${entry_price:.3f} | Size: ${position_size:.2f}")
        self._add_log(f"   Target: ${target_price:.3f} | Stop: ${stop_price:.3f}")
        
        if config.DRY_RUN_MODE:
            self._add_log(f"   ⚠️ DRY RUN - No real trade")
        
        # Record position
        try:
            end_date_str = market.get('end_date_iso')
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')) if end_date_str else None
        except:
            end_date = None
        
        self.position_manager.open_position(
            market_id=market_id,
            market_question=market_question,
            signal=signal,
            entry_price=entry_price,
            target_price=target_price,
            stop_price=stop_price,
            position_size=position_size,
            market_end_date=end_date
        )
        
        position = self.position_manager.get_position(market_id)
        self.trade_logger.log_trade_entry(position, reason)
    
    def _execute_exit(self, position, exit_price, reason):
        """Execute exit trade"""
        self._add_log(f"📉 EXIT: {position['market_question'][:50]}...")
        self._add_log(f"   Entry: ${position['entry_price']:.3f} → Exit: ${exit_price:.3f}")
        
        if config.DRY_RUN_MODE:
            self._add_log(f"   ⚠️ DRY RUN - No real trade")
        
        closed_position = self.position_manager.close_position(
            position['market_id'],
            exit_price,
            reason
        )
        
        self.risk_controller.record_trade(closed_position['pnl'])
        self.trade_logger.log_trade_exit(closed_position)
        
        self._add_log(f"   💰 P&L: ${closed_position['pnl']:+.2f} ({closed_position['pnl_pct']:+.1f}%)")
    
    def _get_order_book(self, market_id: str) -> Optional[Dict]:
        """Get order book for market"""
        try:
            return self.polymarket.get_order_book(market_id)
        except:
            return None
    
    def _get_current_price(self, order_book: Dict, signal: str) -> float:
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
    
    def _add_log(self, message: str):
        """Add message to logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
        
        # Keep last 100 logs
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status"""
        return {
            'is_running': self.is_running,
            'iteration': self.iteration,
            'last_scan': self.last_scan_time,
            'status_message': self.status_message,
            'bankroll': self.risk_controller.current_bankroll,
            'daily_pnl': self.risk_controller.get_daily_pnl(),
            'total_pnl': self.risk_controller.get_total_pnl(),
            'open_positions': len(self.position_manager.get_open_positions()),
            'deployed_capital': self.position_manager.get_deployed_capital(),
            'consecutive_losses': self.risk_controller.consecutive_losses,
            'trading_halted': self.risk_controller.trading_halted
        }
    
    def get_logs(self, last_n: int = 20) -> List[str]:
        """Get recent logs"""
        return self.logs[-last_n:]
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions"""
        return self.position_manager.get_open_positions()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self.trade_logger.get_performance_stats()
