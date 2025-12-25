"""
Signal Generator Module
Calculates fair value and generates entry/exit signals based on strategy rules
"""
from typing import Optional, Dict, Any, Tuple
from enum import Enum
import logging

from automated_trader import config

logger = logging.getLogger(__name__)


class Signal(Enum):
    """Trading signal types"""
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    SELL = "SELL"
    HOLD = "HOLD"
    NO_SIGNAL = "NO_SIGNAL"


class SignalGenerator:
    """Generates trading signals based on fair value and edge calculation"""
    
    def calculate_fair_value(self, order_book: Dict[str, Any]) -> Optional[float]:
        """
        Calculate fair probability as midpoint between best YES and best NO prices
        
        Fair probability = midpoint between best YES ask and best NO ask
        
        Args:
            order_book: Order book with bids and asks for YES and NO
            
        Returns:
            Fair probability (0-1) or None if unable to calculate
        """
        try:
            # Get best prices from order book
            yes_asks = order_book.get('yes', {}).get('asks', [])
            no_asks = order_book.get('no', {}).get('asks', [])
            
            if not yes_asks or not no_asks:
                logger.debug("Missing asks in order book")
                return None
            
            # Best ask is the lowest price someone is willing to sell at
            best_yes_price = min([float(ask['price']) for ask in yes_asks])
            best_no_price = min([float(ask['price']) for ask in no_asks])
            
            # Fair value is the midpoint
            # Since YES + NO should = 1, we can calculate implied probability
            fair_value = best_yes_price / (best_yes_price + best_no_price)
            
            logger.debug(f"Fair value: {fair_value:.3f} (YES: {best_yes_price:.3f}, NO: {best_no_price:.3f})")
            return fair_value
            
        except Exception as e:
            logger.error(f"Failed to calculate fair value: {e}")
            return None
    
    def generate_entry_signal(
        self, 
        market: Dict[str, Any],
        fair_value: float
    ) -> Tuple[Signal, Optional[float], str]:
        """
        Generate entry signal based on edge requirement
        
        Entry Rules:
        - Buy YES if: best_yes_price <= fair_value - EDGE_REQUIRED
        - Buy NO if: best_no_price <= (1 - fair_value) - EDGE_REQUIRED
        
        Args:
            market: Market data with order book
            fair_value: Calculated fair probability
            
        Returns:
            (Signal, entry_price, reason) tuple
        """
        try:
            order_book = market.get('order_book', {})
            
            # Get best ask prices
            yes_asks = order_book.get('yes', {}).get('asks', [])
            no_asks = order_book.get('no', {}).get('asks', [])
            
            if not yes_asks or not no_asks:
                return Signal.NO_SIGNAL, None, "Missing order book data"
            
            best_yes_price = min([float(ask['price']) for ask in yes_asks])
            best_no_price = min([float(ask['price']) for ask in no_asks])
            
            # Check YES entry condition
            yes_edge = fair_value - best_yes_price
            if yes_edge >= config.EDGE_REQUIRED:
                reason = f"BUY YES @ ${best_yes_price:.3f} - Edge: {yes_edge:.1%} (Fair: {fair_value:.1%})"
                logger.info(f"✓ {reason}")
                return Signal.BUY_YES, best_yes_price, reason
            
            # Check NO entry condition
            fair_no = 1.0 - fair_value
            no_edge = fair_no - best_no_price
            if no_edge >= config.EDGE_REQUIRED:
                reason = f"BUY NO @ ${best_no_price:.3f} - Edge: {no_edge:.1%} (Fair: {fair_no:.1%})"
                logger.info(f"✓ {reason}")
                return Signal.BUY_NO, best_no_price, reason
            
            # No sufficient edge found
            yes_edge_pct = yes_edge * 100
            no_edge_pct = no_edge * 100
            required_pct = config.EDGE_REQUIRED * 100
            return Signal.NO_SIGNAL, None, f"No edge (YES: {yes_edge_pct:.1f}%, NO: {no_edge_pct:.1f}% < {required_pct:.0f}% required)"
            
        except Exception as e:
            logger.error(f"Failed to generate entry signal: {e}")
            return Signal.NO_SIGNAL, None, f"Error: {e}"
    
    def calculate_exit_price(self, entry_price: float, signal: Signal) -> float:
        """
        Calculate limit sell price for profit target
        
        Exit at entry_price + PROFIT_TARGET
        
        Args:
            entry_price: Original entry price
            signal: Entry signal (BUY_YES or BUY_NO)
            
        Returns:
            Target exit price
        """
        exit_price = entry_price + config.PROFIT_TARGET
        
        # Cap at 1.0 (100% probability)
        exit_price = min(exit_price, 0.99)
        
        logger.debug(f"Exit target: {exit_price:.3f} (entry: {entry_price:.3f} + {config.PROFIT_TARGET})")
        return exit_price
    
    def calculate_stop_loss_price(self, entry_price: float) -> float:
        """
        Calculate stop loss price
        
        Stop at entry_price * (1 + STOP_LOSS_PCT)
        
        Args:
            entry_price: Original entry price
            
        Returns:
            Stop loss price
        """
        stop_price = entry_price * (1.0 + config.STOP_LOSS_PCT)
        
        # Floor at 0.01 (minimum price)
        stop_price = max(stop_price, 0.01)
        
        logger.debug(f"Stop loss: {stop_price:.3f} (entry: {entry_price:.3f}, {config.STOP_LOSS_PCT:.0%})")
        return stop_price
    
    def should_exit_position(
        self,
        position: Dict[str, Any],
        current_price: float
    ) -> Tuple[bool, str]:
        """
        Check if position should be exited based on exit rules
        
        Exit conditions:
        1. Profit target hit
        2. Stop loss hit
        3. Position timeout (72 hours)
        4. Approaching resolution date
        
        Args:
            position: Position data with entry details
            current_price: Current market price
            
        Returns:
            (should_exit, reason) tuple
        """
        from datetime import datetime, timedelta
        
        entry_price = position['entry_price']
        target_price = position['target_price']
        stop_price = position['stop_price']
        entry_time = position['entry_time']
        
        # Check profit target
        if current_price >= target_price:
            return True, f"Profit target hit: {current_price:.3f} >= {target_price:.3f}"
        
        # Check stop loss
        if current_price <= stop_price:
            return True, f"Stop loss hit: {current_price:.3f} <= {stop_price:.3f}"
        
        # Check timeout
        hours_open = (datetime.now() - entry_time).total_seconds() / 3600
        if hours_open >= config.POSITION_TIMEOUT_HOURS:
            return True, f"Position timeout: {hours_open:.1f}h >= {config.POSITION_TIMEOUT_HOURS}h"
        
        # Check if approaching resolution
        market_end = position.get('market_end_date')
        if market_end and config.NEVER_HOLD_THROUGH_RESOLUTION:
            time_to_end = (market_end - datetime.now()).total_seconds() / 3600
            if time_to_end < 24:  # Exit if less than 24 hours to resolution
                return True, f"Approaching resolution: {time_to_end:.1f}h remaining"
        
        return False, "No exit condition met"
