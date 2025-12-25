"""
Position Manager Module
Tracks open positions, handles partial fills, enforces position limits
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import logging

from automated_trader import config
from automated_trader.signal_generator import Signal

logger = logging.getLogger(__name__)


class PositionStatus(Enum):
    """Position lifecycle status"""
    OPENING = "OPENING"        # Order placed, not fully filled
    OPEN = "OPEN"              # Position fully entered
    CLOSING = "CLOSING"        # Exit order placed
    CLOSED = "CLOSED"          # Position fully exited


class PositionManager:
    """Manages open positions and enforces position sizing limits"""
    
    def __init__(self):
        self.positions: Dict[str, Dict[str, Any]] = {}  # market_id -> position
        self.closed_positions: List[Dict[str, Any]] = []
        
    def can_open_position(self, bankroll: float) -> Tuple[bool, str]:
        """
        Check if new position can be opened based on limits
        
        Checks:
        - Max concurrent positions
        - Max deployed capital percentage
        
        Args:
            bankroll: Current total bankroll
            
        Returns:
            (can_open, reason) tuple
        """
        # Check max concurrent positions
        open_count = len([p for p in self.positions.values() 
                         if p['status'] in [PositionStatus.OPEN, PositionStatus.OPENING]])
        
        if open_count >= config.MAX_CONCURRENT_POSITIONS:
            return False, f"Max concurrent positions reached: {open_count}/{config.MAX_CONCURRENT_POSITIONS}"
        
        # Check max deployed capital
        deployed = self.get_deployed_capital()
        max_deployed = bankroll * config.MAX_DEPLOYED_PCT
        
        if deployed >= max_deployed:
            return False, f"Max deployed capital reached: ${deployed:.2f}/${max_deployed:.2f}"
        
        return True, "OK"
    
    def calculate_position_size(self, bankroll: float, entry_price: float) -> float:
        """
        Calculate position size based on bankroll and limits
        
        Position size = min(
            MAX_POSITION_SIZE_PCT * bankroll,
            remaining_deployable_capital
        )
        
        Args:
            bankroll: Current total bankroll
            entry_price: Entry price for the position
            
        Returns:
            Position size in USD
        """
        # Max size per position
        max_size = bankroll * config.MAX_POSITION_SIZE_PCT
        
        # Remaining deployable capital
        deployed = self.get_deployed_capital()
        max_deployed = bankroll * config.MAX_DEPLOYED_PCT
        remaining = max_deployed - deployed
        
        # Take the minimum
        position_size = min(max_size, remaining)
        
        logger.debug(f"Position size: ${position_size:.2f} (max: ${max_size:.2f}, remaining: ${remaining:.2f})")
        return position_size
    
    def open_position(
        self,
        market_id: str,
        market_question: str,
        signal: Signal,
        entry_price: float,
        target_price: float,
        stop_price: float,
        position_size: float,
        market_end_date: Optional[datetime] = None
    ) -> str:
        """
        Open a new position
        
        Args:
            market_id: Unique market identifier
            market_question: Market question text
            signal: Entry signal (BUY_YES or BUY_NO)
            entry_price: Entry price
            target_price: Profit target price
            stop_price: Stop loss price
            position_size: Position size in USD
            market_end_date: Market resolution date
            
        Returns:
            Position ID
        """
        position_id = f"{market_id}_{datetime.now().timestamp()}"
        
        position = {
            'position_id': position_id,
            'market_id': market_id,
            'market_question': market_question,
            'signal': signal.value,
            'entry_price': entry_price,
            'target_price': target_price,
            'stop_price': stop_price,
            'position_size': position_size,
            'shares': position_size / entry_price,  # Convert USD to shares
            'entry_time': datetime.now(),
            'market_end_date': market_end_date,
            'status': PositionStatus.OPEN,
            'fill_price': entry_price,  # Assume full fill at entry price initially
            'partial_fills': []
        }
        
        self.positions[market_id] = position
        
        logger.info(f"✓ Opened position: {market_question[:50]}... "
                   f"({signal.value} @ {entry_price:.3f}, size: ${position_size:.2f})")
        
        return position_id
    
    def close_position(
        self,
        market_id: str,
        exit_price: float,
        reason: str
    ) -> Dict[str, Any]:
        """
        Close an existing position and calculate P&L
        
        Args:
            market_id: Market identifier
            exit_price: Exit price
            reason: Reason for closing
            
        Returns:
            Closed position with P&L data
        """
        if market_id not in self.positions:
            raise ValueError(f"Position {market_id} not found")
        
        position = self.positions[market_id]
        
        # Calculate P&L
        entry_value = position['position_size']
        exit_value = position['shares'] * exit_price
        pnl = exit_value - entry_value
        pnl_pct = (pnl / entry_value) * 100
        
        # Update position
        position['exit_price'] = exit_price
        position['exit_time'] = datetime.now()
        position['exit_reason'] = reason
        position['pnl'] = pnl
        position['pnl_pct'] = pnl_pct
        position['status'] = PositionStatus.CLOSED
        
        # Move to closed positions
        self.closed_positions.append(position)
        del self.positions[market_id]
        
        logger.info(f"✓ Closed position: {position['market_question'][:50]}... "
                   f"(P&L: ${pnl:+.2f} / {pnl_pct:+.1f}%, Reason: {reason})")
        
        return position
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all currently open positions"""
        return list(self.positions.values())
    
    def get_position(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Get specific position by market ID"""
        return self.positions.get(market_id)
    
    def has_position(self, market_id: str) -> bool:
        """Check if position exists for market"""
        return market_id in self.positions
    
    def get_deployed_capital(self) -> float:
        """Calculate total capital currently deployed"""
        return sum(p['position_size'] for p in self.positions.values())
    
    def get_closed_positions_today(self) -> List[Dict[str, Any]]:
        """Get positions closed today"""
        today = datetime.now().date()
        return [p for p in self.closed_positions 
                if p.get('exit_time') and p['exit_time'].date() == today]
    
    def handle_partial_fill(
        self,
        market_id: str,
        filled_size: float,
        fill_price: float
    ):
        """
        Handle partial order fill
        
        Args:
            market_id: Market identifier
            filled_size: Amount filled in USD
            fill_price: Price of fill
        """
        if market_id not in self.positions:
            logger.warning(f"Partial fill for unknown position: {market_id}")
            return
        
        position = self.positions[market_id]
        
        fill_data = {
            'size': filled_size,
            'price': fill_price,
            'time': datetime.now()
        }
        
        position['partial_fills'].append(fill_data)
        
        # Recalculate average fill price
        total_filled = sum(f['size'] for f in position['partial_fills'])
        weighted_price = sum(f['size'] * f['price'] for f in position['partial_fills']) / total_filled
        
        position['fill_price'] = weighted_price
        position['shares'] = total_filled / weighted_price
        
        logger.info(f"Partial fill: {market_id} - ${filled_size:.2f} @ {fill_price:.3f} "
                   f"(Total: ${total_filled:.2f}, Avg: {weighted_price:.3f})")
