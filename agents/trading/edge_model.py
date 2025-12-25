"""
Edge Detection Model
Calculates trading edge by comparing model probabilities to market prices.
Supports relaxed thresholds for EOY mode and target price calculation.

SAFETY FEATURES (Dec 2025):
- Sports market detection and conservative handling
- Hard sanity caps to prevent absurd predictions
- High-volume market guardrails
- Automatic skip of miscalibrated recommendations
"""
import logging
import re
from typing import Optional, Tuple, List
from dataclasses import dataclass, field
from enum import Enum

from agents.trading.api_client import Market

logger = logging.getLogger(__name__)


# ==============================================================================
# SPORTS DETECTION KEYWORDS
# ==============================================================================
SPORTS_KEYWORDS = [
    # Major championships
    "super bowl", "world series", "world cup", "stanley cup", "nba finals",
    "championship", "champion", "playoffs", "win the",
    # Leagues
    "nfl", "nba", "mlb", "nhl", "mls", "premier league", "la liga",
    # Actions
    "mvp", "player prop", "score", "touchdown", "home run", "goal",
    # Teams (common suffixes)
    "vs", "versus", "beat", "defeat",
    # NFL Teams (for direct detection)
    "49ers", "bears", "bengals", "bills", "broncos", "browns", "buccaneers",
    "cardinals", "chargers", "chiefs", "colts", "commanders", "cowboys",
    "dolphins", "eagles", "falcons", "giants", "jaguars", "jets", "lions",
    "packers", "panthers", "patriots", "raiders", "rams", "ravens", "saints",
    "seahawks", "steelers", "texans", "titans", "vikings"
]


def is_sports_market(question: str) -> bool:
    """Detect if a market is sports-related"""
    q_lower = question.lower()
    for keyword in SPORTS_KEYWORDS:
        if keyword in q_lower:
            return True
    return False


def is_super_bowl_market(question: str) -> bool:
    """Specifically detect Super Bowl markets"""
    return "super bowl" in question.lower()


# ==============================================================================
# SANITY CAP FUNCTIONS
# ==============================================================================
def apply_sanity_caps(
    model_prob: float, 
    market_prob: float, 
    total_volume: float,
    question: str
) -> Tuple[float, str]:
    """
    Apply hard sanity caps to prevent absurd predictions.
    
    Returns:
        Tuple of (capped_probability, reason_if_capped)
    """
    original_prob = model_prob
    reason = ""
    
    # Rule 1: High volume markets - max 20% deviation from market
    if total_volume > 100_000:
        max_deviation = 0.20
        min_allowed = max(0.01, market_prob - max_deviation)
        max_allowed = min(0.99, market_prob + max_deviation)
        
        if model_prob < min_allowed:
            model_prob = min_allowed
            reason = f"Capped from {original_prob*100:.0f}% (high-vol market, max {max_deviation*100:.0f}% deviation)"
        elif model_prob > max_allowed:
            model_prob = max_allowed
            reason = f"Capped from {original_prob*100:.0f}% (high-vol market, max {max_deviation*100:.0f}% deviation)"
    
    # Rule 2: Sports championship markets - max 10% deviation, never >50% on longshots
    if is_sports_market(question):
        # Super Bowl and major championships - very strict
        if is_super_bowl_market(question) or "championship" in question.lower():
            max_deviation = 0.10
            max_allowed = min(0.99, market_prob + max_deviation)
            
            # Never allow >50% on any team unless market already >40%
            if market_prob < 0.40 and model_prob > 0.50:
                model_prob = min(0.50, market_prob + max_deviation)
                reason = f"Sports cap: {original_prob*100:.0f}%→{model_prob*100:.0f}% (championship market)"
            elif model_prob > max_allowed:
                model_prob = max_allowed
                reason = f"Sports cap: {original_prob*100:.0f}%→{model_prob*100:.0f}% (max +10% over market)"
    
    # Rule 3: Extreme prices (<5¢ or >95¢) - require model within 5%
    if market_prob < 0.05 or market_prob > 0.95:
        max_deviation = 0.05
        min_allowed = max(0.01, market_prob - max_deviation)
        max_allowed = min(0.99, market_prob + max_deviation)
        
        if model_prob < min_allowed or model_prob > max_allowed:
            model_prob = max(min_allowed, min(max_allowed, model_prob))
            reason = f"Extreme price cap: {original_prob*100:.0f}%→{model_prob*100:.0f}%"
    
    return model_prob, reason


class TradeAction(Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    NO_TRADE = "NO_TRADE"


@dataclass
class EdgeConfig:
    """Configuration for edge detection"""
    # Minimum edge thresholds
    min_edge_percent: float = 5.0        # 5% minimum edge for standard markets
    min_edge_short_term: float = 8.0     # 8% minimum edge for <14 day markets
    min_edge_sports: float = 15.0        # 15% minimum for sports (higher bar)
    short_term_days: int = 14            # Days threshold for short-term
    
    # Maximum slippage assumption
    expected_slippage: float = 1.0       # 1% slippage buffer
    
    # ROI requirements for short-term bets
    min_roi_short_term: float = 10.0     # 10% potential ROI for <14 day markets
    
    # EOY/Relaxed mode flag
    relaxed_mode: bool = False
    
    # Target price discount for limit orders
    limit_order_discount: float = 0.02   # 2% discount for limit orders
    
    # Safety guardrails
    apply_sanity_caps: bool = True       # Apply probability caps
    max_edge_high_volume: float = 30.0   # Max believable edge in high-vol markets


def get_relaxed_edge_config() -> EdgeConfig:
    """Get relaxed edge config for EOY mode"""
    return EdgeConfig(
        min_edge_percent=5.0,        # 5% base edge (down from higher values)
        min_edge_short_term=8.0,     # 8% for <14 days
        min_edge_sports=15.0,        # 15% for sports (skeptical)
        short_term_days=14,
        expected_slippage=1.0,
        min_roi_short_term=10.0,
        relaxed_mode=True,
        limit_order_discount=0.02,
        apply_sanity_caps=True,
        max_edge_high_volume=30.0
    )


@dataclass
class EdgeAnalysis:
    """Results of edge analysis for a market"""
    market: Market
    model_yes_prob: float
    model_no_prob: float
    market_yes_price: float
    market_no_price: float
    yes_edge: float  # Positive = undervalued
    no_edge: float   # Positive = undervalued
    recommended_action: TradeAction
    edge_percent: float
    meets_threshold: bool
    reason: str
    # New fields for enhanced recommendations
    target_price: float = 0.0          # Suggested limit order price
    potential_roi: float = 0.0         # Expected ROI if model is correct
    confidence: str = "medium"         # low/medium/high based on edge size
    # Safety flags
    is_sports: bool = False            # Sports market flag
    was_capped: bool = False           # Model probability was capped
    cap_reason: str = ""               # Reason for cap
    warning: str = ""                  # Warning message for user


class EdgeDetector:
    """
    Detects trading edge by comparing model predictions to market prices.
    """
    
    def __init__(self, config: Optional[EdgeConfig] = None):
        self.config = config or EdgeConfig()
    
    def analyze_edge(
        self, 
        market: Market, 
        model_yes_prob: float,
        model_no_prob: Optional[float] = None
    ) -> EdgeAnalysis:
        """
        Analyze trading edge for a market.
        
        Args:
            market: Market object with current prices
            model_yes_prob: Model's probability for YES (0-1 or 0-100)
            model_no_prob: Model's probability for NO (optional, computed from YES)
            
        Returns:
            EdgeAnalysis with recommendation
        """
        # Normalize probabilities
        if model_yes_prob > 1:
            model_yes_prob = model_yes_prob / 100
        
        if model_no_prob is None:
            model_no_prob = 1 - model_yes_prob
        elif model_no_prob > 1:
            model_no_prob = model_no_prob / 100
        
        # Get market prices
        market_yes = market.yes_price
        market_no = market.no_price
        
        # Detect sports market
        is_sports = is_sports_market(market.question)
        is_super_bowl = is_super_bowl_market(market.question)
        
        # Initialize safety tracking
        was_capped = False
        cap_reason = ""
        warning = ""
        original_model_yes = model_yes_prob
        
        # ==================================================================
        # APPLY SANITY CAPS (Critical Safety Feature)
        # ==================================================================
        if self.config.apply_sanity_caps:
            total_volume = market.volume or 0
            
            # Apply caps to YES probability
            model_yes_prob, cap_reason = apply_sanity_caps(
                model_yes_prob, market_yes, total_volume, market.question
            )
            
            if cap_reason:
                was_capped = True
                model_no_prob = 1 - model_yes_prob
                logger.warning(f"Sanity cap applied: {cap_reason}")
        
        # ==================================================================
        # SUPER BOWL GUARDRAIL (Immediate Safety)
        # ==================================================================
        if is_super_bowl and abs(model_yes_prob - market_yes) > 0.20:
            # Force skip on Super Bowl with >20% edge claim
            logger.warning(f"🚫 Super Bowl guardrail: Model {original_model_yes*100:.0f}% vs Market {market_yes*100:.0f}%")
            return EdgeAnalysis(
                market=market,
                model_yes_prob=model_yes_prob,
                model_no_prob=model_no_prob,
                market_yes_price=market_yes,
                market_no_price=market_no,
                yes_edge=0,
                no_edge=0,
                recommended_action=TradeAction.NO_TRADE,
                edge_percent=0,
                meets_threshold=False,
                reason="Sports miscalibration guardrail triggered (Super Bowl)",
                target_price=0,
                potential_roi=0,
                confidence="low",
                is_sports=True,
                was_capped=True,
                cap_reason="Super Bowl market - automatic skip",
                warning="⚠️ Sports markets have high miscalibration risk"
            )
        
        # Calculate edges (positive = undervalued, good to buy)
        yes_edge = (model_yes_prob - market_yes) * 100  # In percentage points
        no_edge = (model_no_prob - market_no) * 100
        
        # ==================================================================
        # DETERMINE REQUIRED THRESHOLD
        # ==================================================================
        days = market.days_to_resolution or 999
        is_short_term = days < self.config.short_term_days
        total_volume = market.volume or 0
        
        # Base threshold
        if is_sports:
            required_edge = self.config.min_edge_sports  # Higher bar for sports
            warning = "⚠️ Sports market - higher risk of miscalibration"
        elif is_short_term:
            required_edge = self.config.min_edge_short_term
        else:
            required_edge = self.config.min_edge_percent
        
        # ==================================================================
        # HIGH-VOLUME MARKET VALIDATION
        # ==================================================================
        if total_volume > 500_000:
            max_believable_edge = self.config.max_edge_high_volume
            if max(yes_edge, no_edge) > max_believable_edge:
                logger.warning(f"Implausible edge in high-volume market: {max(yes_edge, no_edge):.1f}%")
                return EdgeAnalysis(
                    market=market,
                    model_yes_prob=model_yes_prob,
                    model_no_prob=model_no_prob,
                    market_yes_price=market_yes,
                    market_no_price=market_no,
                    yes_edge=yes_edge,
                    no_edge=no_edge,
                    recommended_action=TradeAction.NO_TRADE,
                    edge_percent=0,
                    meets_threshold=False,
                    reason=f"Implausible {max(yes_edge, no_edge):.1f}% edge in ${total_volume/1e6:.1f}M volume market",
                    target_price=0,
                    potential_roi=0,
                    confidence="low",
                    is_sports=is_sports,
                    was_capped=was_capped,
                    cap_reason=cap_reason,
                    warning="High-volume markets are efficiently priced"
                )
        
        # Account for slippage
        effective_yes_edge = yes_edge - self.config.expected_slippage
        effective_no_edge = no_edge - self.config.expected_slippage
        
        # Calculate potential ROI for each side
        yes_roi = ((model_yes_prob - market_yes) / market_yes * 100) if market_yes > 0 else 0
        no_roi = ((model_no_prob - market_no) / market_no * 100) if market_no > 0 else 0
        
        # Determine best action
        action = TradeAction.NO_TRADE
        best_edge = 0
        target_price = 0
        potential_roi = 0
        reason = "No significant edge detected"
        
        if effective_yes_edge >= required_edge and effective_yes_edge > effective_no_edge:
            # Check ROI requirement for short-term
            if is_short_term and yes_roi < self.config.min_roi_short_term:
                reason = f"YES edge {effective_yes_edge:.1f}% but ROI {yes_roi:.1f}% < {self.config.min_roi_short_term:.1f}% required for short-term"
            else:
                action = TradeAction.BUY_YES
                best_edge = effective_yes_edge
                potential_roi = yes_roi
                # Target price: current price * (1 - discount) for limit orders
                target_price = market_yes * (1 - self.config.limit_order_discount)
                reason = f"YES undervalued by {best_edge:.1f}% (model: {model_yes_prob*100:.1f}%, market: {market_yes*100:.1f}%)"
        elif effective_no_edge >= required_edge and effective_no_edge > effective_yes_edge:
            # Check ROI requirement for short-term
            if is_short_term and no_roi < self.config.min_roi_short_term:
                reason = f"NO edge {effective_no_edge:.1f}% but ROI {no_roi:.1f}% < {self.config.min_roi_short_term:.1f}% required for short-term"
            else:
                action = TradeAction.BUY_NO
                best_edge = effective_no_edge
                potential_roi = no_roi
                target_price = market_no * (1 - self.config.limit_order_discount)
                reason = f"NO undervalued by {best_edge:.1f}% (model: {model_no_prob*100:.1f}%, market: {market_no*100:.1f}%)"
        else:
            # No edge meets threshold
            if max(effective_yes_edge, effective_no_edge) > 0:
                reason = f"Edge too small: {max(effective_yes_edge, effective_no_edge):.1f}% < {required_edge:.1f}% required"
            else:
                reason = f"Market fairly priced (model ≈ market)"
        
        # Determine confidence level
        if best_edge >= 15:
            confidence = "high"
        elif best_edge >= 10:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Sports market confidence downgrade
        if is_sports and confidence != "low":
            confidence = "low"  # Always low confidence on sports
        
        return EdgeAnalysis(
            market=market,
            model_yes_prob=model_yes_prob,
            model_no_prob=model_no_prob,
            market_yes_price=market_yes,
            market_no_price=market_no,
            yes_edge=yes_edge,
            no_edge=no_edge,
            recommended_action=action,
            edge_percent=best_edge,
            meets_threshold=action != TradeAction.NO_TRADE,
            reason=reason,
            target_price=target_price,
            potential_roi=potential_roi,
            confidence=confidence,
            is_sports=is_sports,
            was_capped=was_capped,
            cap_reason=cap_reason,
            warning=warning
        )
    
    def rank_opportunities(
        self, 
        analyses: List[EdgeAnalysis]
    ) -> List[EdgeAnalysis]:
        """
        Rank trading opportunities by edge size.
        
        Returns:
            List sorted by edge (highest first), filtered to only tradeable
        """
        tradeable = [a for a in analyses if a.meets_threshold]
        return sorted(tradeable, key=lambda x: -x.edge_percent)


def parse_model_probability(llm_response: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Parse probability from LLM response.
    
    Handles formats like:
    - "likelihood `0.6` for outcome of `Yes`"
    - "60% probability for Yes"
    - "I estimate 0.35 for Yes"
    
    Returns:
        (probability, outcome) or (None, None) if parsing fails
    """
    import re
    
    # Pattern 1: likelihood `X.X` for outcome of `Yes/No`
    match = re.search(r'likelihood\s*[`\'"]*([0-9.]+)[%]?[`\'"]*\s*for\s*outcome\s*of\s*[`\'"]*(\w+)', llm_response, re.IGNORECASE)
    if match:
        prob = float(match.group(1))
        outcome = match.group(2)
        return (prob if prob <= 1 else prob/100, outcome)
    
    # Pattern 2: X% probability for Yes/No
    match = re.search(r'([0-9.]+)\s*%?\s*(?:probability|chance|likelihood)\s*(?:for|of)\s*(\w+)', llm_response, re.IGNORECASE)
    if match:
        prob = float(match.group(1))
        outcome = match.group(2)
        return (prob if prob <= 1 else prob/100, outcome)
    
    # Pattern 3: Just a number in backticks
    match = re.search(r'[`\'"]([0-9.]+)[%]?[`\'"]', llm_response)
    if match:
        prob = float(match.group(1))
        return (prob if prob <= 1 else prob/100, "Yes")  # Assume Yes if not specified
    
    return (None, None)
