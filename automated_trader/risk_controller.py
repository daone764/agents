"""
Risk Controller Module
Enforces daily loss limits and consecutive loss rules
"""
from datetime import datetime, date
from typing import List, Dict, Any
import logging

from automated_trader import config

logger = logging.getLogger(__name__)


class RiskController:
    """Controls risk through loss limits and position constraints"""
    
    def __init__(self, initial_bankroll: float):
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        
        # Consecutive losses tracking
        self.consecutive_losses = 0
        self.last_trade_date = None
        
        # Daily tracking
        self.daily_start_bankroll = initial_bankroll
        self.daily_pnl = 0.0
        
        # Trading halt flag
        self.trading_halted = False
        self.halt_reason = None
        
    def can_trade(self) -> tuple[bool, str]:
        """
        Check if trading is allowed based on risk rules
        
        Checks:
        - Not currently halted
        - Below consecutive loss limit
        - Below daily loss limit
        
        Returns:
            (can_trade, reason) tuple
        """
        if self.trading_halted:
            return False, f"Trading halted: {self.halt_reason}"
        
        # Check consecutive losses
        if self.consecutive_losses >= config.MAX_CONSECUTIVE_LOSSES:
            self.halt_trading(f"Hit consecutive loss limit: {self.consecutive_losses}")
            return False, self.halt_reason
        
        # Check daily loss limit
        daily_loss_pct = (self.daily_pnl / self.daily_start_bankroll) * 100
        max_loss_pct = config.DAILY_MAX_LOSS_PCT * 100
        
        if self.daily_pnl < 0 and abs(daily_loss_pct) >= max_loss_pct:
            self.halt_trading(f"Hit daily loss limit: {daily_loss_pct:.1f}% >= {max_loss_pct:.1f}%")
            return False, self.halt_reason
        
        return True, "OK"
    
    def record_trade(self, pnl: float, trade_date: date = None):
        """
        Record a completed trade and update risk metrics
        
        Args:
            pnl: Profit/loss from trade
            trade_date: Date of trade (defaults to today)
        """
        if trade_date is None:
            trade_date = datetime.now().date()
        
        # Update bankroll
        self.current_bankroll += pnl
        self.daily_pnl += pnl
        
        # Update consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
            logger.warning(f"Loss recorded: ${pnl:.2f} (Consecutive losses: {self.consecutive_losses})")
        else:
            # Reset on winning trade
            if self.consecutive_losses > 0:
                logger.info(f"Winning trade breaks {self.consecutive_losses} loss streak")
            self.consecutive_losses = 0
        
        # Check if new day (reset daily metrics)
        if config.RESET_LOSS_COUNTER_DAILY:
            if self.last_trade_date and trade_date > self.last_trade_date:
                self._reset_daily_metrics()
        
        self.last_trade_date = trade_date
        
        # Log current status
        self._log_status()
    
    def halt_trading(self, reason: str):
        """
        Halt all trading activity
        
        Args:
            reason: Reason for halt
        """
        self.trading_halted = True
        self.halt_reason = reason
        logger.critical(f"🛑 TRADING HALTED: {reason}")
    
    def resume_trading(self):
        """Resume trading after halt"""
        if self.trading_halted:
            logger.info(f"✓ Trading resumed (was: {self.halt_reason})")
            self.trading_halted = False
            self.halt_reason = None
    
    def get_available_capital(self) -> float:
        """Get current available trading capital"""
        return self.current_bankroll
    
    def get_daily_pnl(self) -> float:
        """Get today's total P&L"""
        return self.daily_pnl
    
    def get_total_pnl(self) -> float:
        """Get total P&L since start"""
        return self.current_bankroll - self.initial_bankroll
    
    def get_total_return_pct(self) -> float:
        """Get total return percentage"""
        return ((self.current_bankroll - self.initial_bankroll) / self.initial_bankroll) * 100
    
    def _reset_daily_metrics(self):
        """Reset daily tracking metrics"""
        logger.info(f"📅 New day - Resetting daily metrics (Yesterday P&L: ${self.daily_pnl:.2f})")
        
        self.daily_start_bankroll = self.current_bankroll
        self.daily_pnl = 0.0
        
        # Reset consecutive losses if configured
        if config.RESET_LOSS_COUNTER_DAILY:
            if self.consecutive_losses > 0:
                logger.info(f"Resetting consecutive loss counter: {self.consecutive_losses} -> 0")
            self.consecutive_losses = 0
        
        # Resume trading if halted due to daily limit
        if self.trading_halted and "daily loss limit" in self.halt_reason.lower():
            self.resume_trading()
    
    def _log_status(self):
        """Log current risk status"""
        total_pnl = self.get_total_pnl()
        total_return = self.get_total_return_pct()
        daily_pnl_pct = (self.daily_pnl / self.daily_start_bankroll) * 100 if self.daily_start_bankroll > 0 else 0
        
        logger.info(
            f"💰 Bankroll: ${self.current_bankroll:.2f} | "
            f"Daily P&L: ${self.daily_pnl:+.2f} ({daily_pnl_pct:+.1f}%) | "
            f"Total P&L: ${total_pnl:+.2f} ({total_return:+.1f}%) | "
            f"Consecutive Losses: {self.consecutive_losses}"
        )
    
    def check_daily_reset(self):
        """Check if we need to reset daily metrics (call this periodically)"""
        today = datetime.now().date()
        
        if self.last_trade_date and today > self.last_trade_date:
            self._reset_daily_metrics()
