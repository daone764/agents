"""
Position Sizing Module
Safe position sizing based on bankroll and market characteristics.
"""
import logging
from typing import Optional
from dataclasses import dataclass

from agents.trading.api_client import Market
from agents.trading.edge_model import EdgeAnalysis, TradeAction

logger = logging.getLogger(__name__)


@dataclass
class PositionConfig:
    """Configuration for position sizing"""
    # Position limits
    max_position_percent: float = 2.0      # Max 2% of bankroll per trade
    max_short_term_percent: float = 1.0    # Max 1% for markets <14 days
    short_term_days: int = 14              # Threshold for short-term
    
    # Portfolio limits
    max_concurrent_positions: int = 5      # Max 5 open positions
    max_deployed_capital: float = 20.0     # Max 20% of bankroll deployed
    
    # Minimum trade size
    min_position_usd: float = 1.0          # Minimum $1 trade
    
    # Kelly criterion dampening (optional)
    kelly_fraction: float = 0.25           # Use 1/4 Kelly for safety


@dataclass
class PositionRecommendation:
    """Position sizing recommendation"""
    should_trade: bool
    position_percent: float
    position_usd: float
    reason: str
    edge_percent: float
    expected_roi: float
    risk_level: str


class PositionSizer:
    """
    Calculates safe position sizes based on edge and risk parameters.
    """
    
    def __init__(
        self, 
        bankroll: float,
        current_positions: int = 0,
        deployed_capital: float = 0,
        config: Optional[PositionConfig] = None
    ):
        self.bankroll = bankroll
        self.current_positions = current_positions
        self.deployed_capital = deployed_capital
        self.config = config or PositionConfig()
    
    def calculate_position(self, analysis: EdgeAnalysis) -> PositionRecommendation:
        """
        Calculate recommended position size for a trade.
        
        Args:
            analysis: EdgeAnalysis from edge detector
            
        Returns:
            PositionRecommendation with size and reasoning
        """
        # Check if we should trade at all
        if not analysis.meets_threshold:
            return PositionRecommendation(
                should_trade=False,
                position_percent=0,
                position_usd=0,
                reason=analysis.reason,
                edge_percent=analysis.edge_percent,
                expected_roi=0,
                risk_level="N/A"
            )
        
        # Check portfolio limits
        if self.current_positions >= self.config.max_concurrent_positions:
            return PositionRecommendation(
                should_trade=False,
                position_percent=0,
                position_usd=0,
                reason=f"Max positions reached ({self.current_positions}/{self.config.max_concurrent_positions})",
                edge_percent=analysis.edge_percent,
                expected_roi=0,
                risk_level="N/A"
            )
        
        deployed_percent = (self.deployed_capital / self.bankroll) * 100 if self.bankroll > 0 else 100
        if deployed_percent >= self.config.max_deployed_capital:
            return PositionRecommendation(
                should_trade=False,
                position_percent=0,
                position_usd=0,
                reason=f"Max capital deployed ({deployed_percent:.1f}% >= {self.config.max_deployed_capital}%)",
                edge_percent=analysis.edge_percent,
                expected_roi=0,
                risk_level="N/A"
            )
        
        # Determine max position based on time to resolution
        days = analysis.market.days_to_resolution or 999
        if days < self.config.short_term_days:
            max_position = self.config.max_short_term_percent
            risk_level = "HIGH (short-term)"
        else:
            max_position = self.config.max_position_percent
            risk_level = "MODERATE"
        
        # Calculate Kelly-optimal position (dampened)
        edge = analysis.edge_percent / 100  # Convert to decimal
        
        if analysis.recommended_action == TradeAction.BUY_YES:
            win_prob = analysis.model_yes_prob
            odds = (1 / analysis.market_yes_price) - 1 if analysis.market_yes_price > 0 else 0
        else:
            win_prob = analysis.model_no_prob
            odds = (1 / analysis.market_no_price) - 1 if analysis.market_no_price > 0 else 0
        
        # Kelly formula: f* = (p * b - q) / b, where p = win prob, q = 1-p, b = odds
        if odds > 0:
            kelly = ((win_prob * odds) - (1 - win_prob)) / odds
            kelly = max(0, kelly) * self.config.kelly_fraction  # Dampened Kelly
            kelly_percent = kelly * 100
        else:
            kelly_percent = 0
        
        # Take minimum of Kelly and max position
        position_percent = min(kelly_percent, max_position)
        
        # Ensure minimum trade size
        position_usd = (position_percent / 100) * self.bankroll
        if position_usd < self.config.min_position_usd:
            return PositionRecommendation(
                should_trade=False,
                position_percent=0,
                position_usd=0,
                reason=f"Position too small: ${position_usd:.2f} < ${self.config.min_position_usd:.2f} min",
                edge_percent=analysis.edge_percent,
                expected_roi=0,
                risk_level=risk_level
            )
        
        # Calculate expected ROI
        if analysis.recommended_action == TradeAction.BUY_YES:
            entry_price = analysis.market_yes_price
            expected_payout = analysis.model_yes_prob * 1.0  # $1 payout if win
        else:
            entry_price = analysis.market_no_price
            expected_payout = analysis.model_no_prob * 1.0
        
        expected_roi = ((expected_payout - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        
        return PositionRecommendation(
            should_trade=True,
            position_percent=round(position_percent, 2),
            position_usd=round(position_usd, 2),
            reason=f"Edge {analysis.edge_percent:.1f}% detected on {analysis.recommended_action.value}",
            edge_percent=analysis.edge_percent,
            expected_roi=round(expected_roi, 1),
            risk_level=risk_level
        )
    
    def update_portfolio_state(self, positions: int, deployed: float):
        """Update current portfolio state"""
        self.current_positions = positions
        self.deployed_capital = deployed
