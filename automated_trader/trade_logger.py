"""
Trade Logger Module
Logs every trade with timestamp, reason, entry, exit, and P&L
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from automated_trader import config

logger = logging.getLogger(__name__)


class TradeLogger:
    """Logs all trades to structured file for analysis"""
    
    def __init__(self, log_file_path: Optional[str] = None):
        """
        Initialize trade logger
        
        Args:
            log_file_path: Path to log file (defaults to config.LOG_FILE_PATH)
        """
        self.log_file_path = log_file_path or config.LOG_FILE_PATH
        
        # Create log directory if it doesn't exist
        log_dir = Path(self.log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Trade logger initialized: {self.log_file_path}")
    
    def log_trade_entry(
        self,
        position: Dict[str, Any],
        reason: str
    ):
        """
        Log trade entry
        
        Args:
            position: Position data
            reason: Entry reason/signal
        """
        if not config.LOG_EVERY_TRADE:
            return
        
        entry_log = {
            'event': 'ENTRY',
            'timestamp': datetime.now().isoformat(),
            'position_id': position['position_id'],
            'market_id': position['market_id'],
            'market_question': position['market_question'],
            'signal': position['signal'],
            'entry_price': position['entry_price'],
            'target_price': position['target_price'],
            'stop_price': position['stop_price'],
            'position_size': position['position_size'],
            'shares': position['shares'],
            'reason': reason
        }
        
        self._write_log(entry_log)
        logger.info(f"📝 Logged entry: {position['market_question'][:50]}...")
    
    def log_trade_exit(
        self,
        position: Dict[str, Any]
    ):
        """
        Log trade exit with P&L
        
        Args:
            position: Closed position with exit data
        """
        if not config.LOG_EVERY_TRADE:
            return
        
        exit_log = {
            'event': 'EXIT',
            'timestamp': datetime.now().isoformat(),
            'position_id': position['position_id'],
            'market_id': position['market_id'],
            'market_question': position['market_question'],
            'signal': position['signal'],
            'entry_price': position['entry_price'],
            'entry_time': position['entry_time'].isoformat(),
            'exit_price': position['exit_price'],
            'exit_time': position['exit_time'].isoformat(),
            'exit_reason': position['exit_reason'],
            'position_size': position['position_size'],
            'shares': position['shares'],
            'pnl': position['pnl'],
            'pnl_pct': position['pnl_pct'],
            'holding_period_hours': (position['exit_time'] - position['entry_time']).total_seconds() / 3600
        }
        
        self._write_log(exit_log)
        logger.info(f"📝 Logged exit: {position['market_question'][:50]}... (P&L: ${position['pnl']:+.2f})")
    
    def log_signal(
        self,
        market: Dict[str, Any],
        signal: str,
        reason: str,
        entry_price: Optional[float] = None
    ):
        """
        Log trading signal (even if not acted upon)
        
        Args:
            market: Market data
            signal: Signal type
            reason: Signal reason
            entry_price: Potential entry price
        """
        signal_log = {
            'event': 'SIGNAL',
            'timestamp': datetime.now().isoformat(),
            'market_id': market.get('condition_id'),
            'market_question': market.get('question'),
            'signal': signal,
            'entry_price': entry_price,
            'reason': reason
        }
        
        self._write_log(signal_log)
    
    def log_risk_event(
        self,
        event_type: str,
        details: Dict[str, Any]
    ):
        """
        Log risk management events (halts, limit hits, etc.)
        
        Args:
            event_type: Type of risk event
            details: Event details
        """
        risk_log = {
            'event': 'RISK_EVENT',
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            **details
        }
        
        self._write_log(risk_log)
        logger.warning(f"⚠️ Risk event: {event_type}")
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log errors and exceptions
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Additional context
        """
        error_log = {
            'event': 'ERROR',
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {}
        }
        
        self._write_log(error_log)
        logger.error(f"❌ Error logged: {error_type} - {error_message}")
    
    def _write_log(self, log_entry: Dict[str, Any]):
        """
        Write log entry to file (JSONL format)
        
        Args:
            log_entry: Log entry dictionary
        """
        try:
            with open(self.log_file_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write log: {e}")
    
    def get_recent_trades(self, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Get recent trade logs
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of recent trade logs
        """
        try:
            trades = []
            with open(self.log_file_path, 'r') as f:
                for line in f:
                    log_entry = json.loads(line)
                    if log_entry['event'] in ['ENTRY', 'EXIT']:
                        trades.append(log_entry)
            
            return trades[-limit:]
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"Failed to read logs: {e}")
            return []
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Calculate performance statistics from logs
        
        Returns:
            Dictionary with win rate, avg P&L, etc.
        """
        try:
            exits = []
            with open(self.log_file_path, 'r') as f:
                for line in f:
                    log_entry = json.loads(line)
                    if log_entry['event'] == 'EXIT':
                        exits.append(log_entry)
            
            if not exits:
                return {'total_trades': 0}
            
            total_trades = len(exits)
            winning_trades = sum(1 for e in exits if e['pnl'] > 0)
            losing_trades = sum(1 for e in exits if e['pnl'] < 0)
            
            total_pnl = sum(e['pnl'] for e in exits)
            avg_pnl = total_pnl / total_trades
            
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            avg_win = sum(e['pnl'] for e in exits if e['pnl'] > 0) / winning_trades if winning_trades > 0 else 0
            avg_loss = sum(e['pnl'] for e in exits if e['pnl'] < 0) / losing_trades if losing_trades > 0 else 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0
            }
            
        except FileNotFoundError:
            return {'total_trades': 0}
        except Exception as e:
            logger.error(f"Failed to calculate stats: {e}")
            return {'error': str(e)}
