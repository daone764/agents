"""
Bracket Strategy Detector
Identifies related bracket/range markets and generates combined strategies.

Example: U.S. Tariff Revenue 2025 brackets (<$100b, $100-200b, $200-300b, etc.)
"""
import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from agents.trading.api_client import Market

logger = logging.getLogger(__name__)


@dataclass
class BracketMarket:
    """A single bracket within a related set"""
    market: Market
    bracket_label: str  # e.g., "<$100b", "$100-200b"
    lower_bound: Optional[float]  # None means unbounded below
    upper_bound: Optional[float]  # None means unbounded above
    yes_price: float
    no_price: float
    model_prob: Optional[float] = None  # From LLM analysis
    recommended_action: Optional[str] = None  # "BUY_YES", "BUY_NO", or None
    edge_percent: float = 0.0


@dataclass
class BracketStrategy:
    """A combined strategy across related bracket markets"""
    topic: str  # e.g., "U.S. Tariff Revenue 2025"
    thesis: str  # e.g., "Betting the UNDER on high revenue scenarios"
    brackets: List[BracketMarket]
    recommended_trades: List[Dict]  # List of {bracket, action, price, edge}
    total_cost: float
    max_payout: float
    expected_roi: float
    confidence: str  # "Low", "Medium", "High", "Medium-High"
    resolution_info: str  # e.g., "Resolution: Early 2026"


class BracketDetector:
    """
    Detects and groups related bracket markets.
    
    Patterns detected:
    - Revenue/amount ranges: <$100b, $100-200b, $200-300b, etc.
    - Percentage ranges: <10%, 10-20%, etc.
    - Numeric ranges: Under 5, 5-10, Over 10, etc.
    """
    
    # Patterns for bracket detection (ORDER MATTERS - more specific patterns first)
    BRACKET_PATTERNS = [
        # Revenue/amount ranges (billions) - ranges FIRST to avoid partial matches
        (r'\$?(\d+(?:\.\d+)?)\s*[bB]?\s*[-–to]+\s*\$?(\d+(?:\.\d+)?)\s*[bB](?:illion)?', 'revenue_range_b'),
        (r'(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*[bB](?:illion)?', 'revenue_range_b'),
        
        # Below threshold
        (r'[<≤](?:\s*than)?\s*\$?(\d+(?:\.\d+)?)\s*[bB](?:illion)?', 'revenue_below_b'),
        (r'[Ll]ess\s+than\s+\$?(\d+(?:\.\d+)?)\s*[bB](?:illion)?', 'revenue_below_b'),
        (r'[Uu]nder\s+\$?(\d+(?:\.\d+)?)\s*[bB](?:illion)?', 'revenue_below_b'),
        
        # Above threshold
        (r'[>≥](?:\s*than)?\s*\$?(\d+(?:\.\d+)?)\s*[bB](?:illion)?', 'revenue_above_b'),
        (r'[Mm]ore\s+than\s+\$?(\d+(?:\.\d+)?)\s*[bB](?:illion)?', 'revenue_above_b'),
        (r'[Oo]ver\s+\$?(\d+(?:\.\d+)?)\s*[bB](?:illion)?', 'revenue_above_b'),
        
        # Percentage brackets - ranges first
        (r'(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*%', 'pct_range'),
        (r'[<≤]\s*(\d+(?:\.\d+)?)\s*%', 'pct_below'),
        (r'[>≥]\s*(\d+(?:\.\d+)?)\s*%', 'pct_above'),
        
        # Generic numeric brackets - ranges first
        (r'(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)', 'range'),
        (r'[Uu]nder\s+(\d+(?:\.\d+)?)', 'under'),
        (r'[Oo]ver\s+(\d+(?:\.\d+)?)', 'over'),
    ]
    
    # Topic extraction patterns
    TOPIC_PATTERNS = [
        r'^(.*?)\s*(?:in\s+\d{4}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
        r'^(.*?)\s*(?:<|>|≤|≥|\d+[-–to])',
        r'^(.*?)\s*[Uu]nder',
        r'^(.*?)\s*[Oo]ver',
    ]
    
    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
    
    def extract_topic(self, question: str) -> str:
        """Extract the base topic from a bracket question"""
        # Remove common suffixes
        question = question.strip()
        question = re.sub(r'\?$', '', question)
        
        for pattern in self.TOPIC_PATTERNS:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                topic = match.group(1).strip()
                if len(topic) > 10:  # Ensure meaningful topic
                    return topic
        
        # Fallback: remove bracket portion
        for pattern, _ in self.BRACKET_PATTERNS:
            question = re.sub(pattern, '', question, flags=re.IGNORECASE)
        
        return question.strip()
    
    def extract_bracket_bounds(self, question: str) -> Tuple[Optional[float], Optional[float], str]:
        """
        Extract bracket bounds from a question.
        
        Returns:
            (lower_bound, upper_bound, bracket_label)
        """
        for pattern, ptype in self.BRACKET_PATTERNS:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                if ptype in ('revenue_below_b', 'pct_below', 'under'):
                    # Below threshold: e.g., "<$100b"
                    val = float(match.group(1))
                    if 'revenue' in ptype:
                        return (None, val, f"<${val:.0f}b")
                    elif 'pct' in ptype:
                        return (None, val, f"<{val:.0f}%")
                    else:
                        return (None, val, f"Under {val:.0f}")
                
                elif ptype in ('revenue_range_b', 'pct_range', 'range'):
                    # Range: e.g., "$100-200b"
                    low = float(match.group(1))
                    high = float(match.group(2))
                    if 'revenue' in ptype:
                        return (low, high, f"${low:.0f}-{high:.0f}b")
                    elif 'pct' in ptype:
                        return (low, high, f"{low:.0f}-{high:.0f}%")
                    else:
                        return (low, high, f"{low:.0f}-{high:.0f}")
                
                elif ptype in ('revenue_above_b', 'pct_above', 'over'):
                    # Above threshold: e.g., ">$500b"
                    val = float(match.group(1))
                    if 'revenue' in ptype:
                        return (val, None, f">${val:.0f}b")
                    elif 'pct' in ptype:
                        return (val, None, f">{val:.0f}%")
                    else:
                        return (val, None, f"Over {val:.0f}")
        
        return (None, None, "Unknown")
        
        return (None, None, "Unknown")
    
    def group_related_markets(self, markets: List[Market]) -> Dict[str, List[BracketMarket]]:
        """
        Group markets by their base topic.
        
        Returns:
            Dict mapping topic -> list of BracketMarkets
        """
        topic_groups = defaultdict(list)
        
        for market in markets:
            question = market.question
            topic = self.extract_topic(question)
            lower, upper, label = self.extract_bracket_bounds(question)
            
            # Only include if we found meaningful brackets
            if label != "Unknown" and (lower is not None or upper is not None):
                bracket = BracketMarket(
                    market=market,
                    bracket_label=label,
                    lower_bound=lower,
                    upper_bound=upper,
                    yes_price=market.yes_price,
                    no_price=market.no_price
                )
                topic_groups[topic].append(bracket)
        
        # Filter to only topics with multiple brackets
        return {
            topic: brackets 
            for topic, brackets in topic_groups.items() 
            if len(brackets) >= 2
        }
    
    def find_bracket_groups(self, markets: List[Market]) -> List[Dict[str, List[BracketMarket]]]:
        """Find all bracket groups in a list of markets"""
        return self.group_related_markets(markets)


class BracketStrategyGenerator:
    """
    Generates combined strategies for bracket markets.
    """
    
    def __init__(self, detector: Optional[BracketDetector] = None):
        self.detector = detector or BracketDetector()
    
    def generate_strategy(
        self,
        topic: str,
        brackets: List[BracketMarket],
        model_forecast: Optional[Dict[str, float]] = None
    ) -> Optional[BracketStrategy]:
        """
        Generate a combined bracket strategy.
        
        Args:
            topic: The base topic (e.g., "U.S. Tariff Revenue 2025")
            brackets: List of BracketMarkets in this group
            model_forecast: Optional dict mapping bracket_label -> model probability
        
        Returns:
            BracketStrategy or None if no good strategy found
        """
        if len(brackets) < 2:
            return None
        
        # Sort brackets by their bounds
        sorted_brackets = sorted(
            brackets,
            key=lambda b: (b.lower_bound or float('-inf'), b.upper_bound or float('inf'))
        )
        
        # Analyze each bracket for edge
        recommended_trades = []
        total_cost = 0
        max_payout = 0
        
        for bracket in sorted_brackets:
            # Use model forecast if available, otherwise use market price as base
            if model_forecast and bracket.bracket_label in model_forecast:
                model_prob = model_forecast[bracket.bracket_label]
            else:
                # Default: estimate based on market price with slight adjustment
                model_prob = bracket.yes_price
            
            bracket.model_prob = model_prob
            
            # Calculate edge for YES
            yes_edge = (model_prob - bracket.yes_price) * 100
            
            # Calculate edge for NO
            no_model_prob = 1 - model_prob
            no_edge = (no_model_prob - bracket.no_price) * 100
            
            # Determine recommended action
            min_edge = 5.0  # Minimum edge threshold
            
            if yes_edge >= min_edge:
                bracket.recommended_action = "BUY_YES"
                bracket.edge_percent = yes_edge
                cost = bracket.yes_price * 100  # Assuming $100 position
                payout = 100  # Full payout if YES wins
                
                recommended_trades.append({
                    'bracket': bracket,
                    'action': 'BUY_YES',
                    'price': bracket.yes_price,
                    'edge': yes_edge,
                    'cost': cost,
                    'payout': payout
                })
                total_cost += cost
                max_payout += payout
                
            elif no_edge >= min_edge:
                bracket.recommended_action = "BUY_NO"
                bracket.edge_percent = no_edge
                cost = bracket.no_price * 100
                payout = 100
                
                recommended_trades.append({
                    'bracket': bracket,
                    'action': 'BUY_NO',
                    'price': bracket.no_price,
                    'edge': no_edge,
                    'cost': cost,
                    'payout': payout
                })
                total_cost += cost
                max_payout += payout
        
        if not recommended_trades:
            return None
        
        # Generate thesis based on trade pattern
        thesis = self._generate_thesis(recommended_trades, sorted_brackets)
        
        # Calculate expected ROI
        # Assume 1-2 brackets win on average
        avg_wins = min(len(recommended_trades), 2)
        expected_payout = avg_wins * 100
        expected_roi = ((expected_payout - total_cost) / total_cost * 100) if total_cost > 0 else 0
        
        # Determine confidence
        avg_edge = sum(t['edge'] for t in recommended_trades) / len(recommended_trades)
        if avg_edge >= 15:
            confidence = "High"
        elif avg_edge >= 10:
            confidence = "Medium-High"
        elif avg_edge >= 7:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        return BracketStrategy(
            topic=topic,
            thesis=thesis,
            brackets=sorted_brackets,
            recommended_trades=recommended_trades,
            total_cost=total_cost,
            max_payout=max_payout,
            expected_roi=expected_roi,
            confidence=confidence,
            resolution_info="Resolution: Early 2026"  # Default, could be extracted from markets
        )
    
    def _generate_thesis(self, trades: List[Dict], all_brackets: List[BracketMarket]) -> str:
        """Generate a thesis explanation for the strategy"""
        if not trades:
            return "No clear thesis"
        
        # Count YES vs NO trades
        yes_trades = [t for t in trades if t['action'] == 'BUY_YES']
        no_trades = [t for t in trades if t['action'] == 'BUY_NO']
        
        # Analyze which end of the range we're betting on
        yes_brackets = [t['bracket'] for t in yes_trades]
        no_brackets = [t['bracket'] for t in no_trades]
        
        # Check if betting low (YES on lower brackets, NO on higher)
        if yes_brackets:
            avg_yes_bound = sum(
                b.upper_bound or b.lower_bound or 0 for b in yes_brackets
            ) / len(yes_brackets)
        else:
            avg_yes_bound = float('inf')
        
        if no_brackets:
            avg_no_bound = sum(
                b.lower_bound or b.upper_bound or 0 for b in no_brackets
            ) / len(no_brackets)
        else:
            avg_no_bound = float('-inf')
        
        if avg_yes_bound < avg_no_bound:
            return "Betting the UNDER on high scenarios. Model expects outcome in lower ranges."
        elif avg_no_bound < avg_yes_bound:
            return "Betting the OVER on low scenarios. Model expects outcome in higher ranges."
        else:
            return "Mixed strategy across bracket ranges."
    
    def format_strategy_text(self, strategy: BracketStrategy) -> str:
        """Format a bracket strategy as text output"""
        output = f"""
{'═'*80}
COMBINED BRACKET STRATEGY: {strategy.topic}
{'═'*80}
Overall Thesis: {strategy.thesis}

Recommended Trades:
"""
        for trade in strategy.recommended_trades:
            bracket = trade['bracket']
            action = trade['action'].replace('_', ' ')
            price = trade['price']
            edge = trade['edge']
            
            if trade['action'] == 'BUY_NO':
                output += f"• {action} on {bracket.bracket_label} @ ~{int(bracket.yes_price*100)}¢ (Yes price) → Edge +{edge:.1f}% on No\n"
            else:
                output += f"• {action} on {bracket.bracket_label} @ ~{int(price*100)}¢ → Edge +{edge:.1f}%\n"
        
        output += f"""
Total estimated cost: ${strategy.total_cost:.0f} for ${strategy.max_payout:.0f} potential payout
Max win scenarios: 1-2 brackets hit → +{strategy.expected_roi:.0f}% return
Max loss: All wrong → –100%

Direct links:
"""
        for trade in strategy.recommended_trades:
            bracket = trade['bracket']
            market = bracket.market
            action_note = " (Buy No)" if trade['action'] == 'BUY_NO' else ""
            output += f"- {bracket.bracket_label}{action_note}: {market.market_url}\n"
        
        output += f"""
Confidence: {strategy.confidence} | {strategy.resolution_info}
{'═'*80}
"""
        return output
    
    def format_strategy_html(self, strategy: BracketStrategy) -> str:
        """Format a bracket strategy as HTML"""
        trades_html = ""
        for trade in strategy.recommended_trades:
            bracket = trade['bracket']
            action = trade['action'].replace('_', ' ')
            price = trade['price']
            edge = trade['edge']
            market = bracket.market
            
            if trade['action'] == 'BUY_NO':
                action_text = f"<strong>{action}</strong> @ ~{int(bracket.yes_price*100)}¢ (Yes price)"
                edge_text = f"Edge <span class='edge-positive'>+{edge:.1f}%</span> on No"
            else:
                action_text = f"<strong>{action}</strong> @ ~{int(price*100)}¢"
                edge_text = f"Edge <span class='edge-positive'>+{edge:.1f}%</span>"
            
            trades_html += f"""
            <div class="bracket-trade">
                <div class="bracket-label">{bracket.bracket_label}</div>
                <div class="bracket-action">{action_text}</div>
                <div class="bracket-edge">{edge_text}</div>
                <a href="{market.market_url}" target="_blank" class="trade-link">Trade →</a>
            </div>
            """
        
        links_html = ""
        for trade in strategy.recommended_trades:
            bracket = trade['bracket']
            market = bracket.market
            action_note = " (Buy No)" if trade['action'] == 'BUY_NO' else ""
            links_html += f'<li><a href="{market.market_url}" target="_blank">{bracket.bracket_label}{action_note}</a></li>'
        
        return f"""
        <div class="bracket-strategy">
            <div class="bracket-header">
                <h3>📊 COMBINED BRACKET STRATEGY</h3>
                <div class="bracket-topic">{strategy.topic}</div>
            </div>
            
            <div class="bracket-thesis">
                <strong>Thesis:</strong> {strategy.thesis}
            </div>
            
            <div class="bracket-trades">
                <h4>Recommended Trades:</h4>
                {trades_html}
            </div>
            
            <div class="bracket-summary">
                <div class="summary-item">
                    <span class="label">Total Cost:</span>
                    <span class="value">${strategy.total_cost:.0f}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Max Payout:</span>
                    <span class="value">${strategy.max_payout:.0f}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Expected ROI:</span>
                    <span class="value edge-positive">+{strategy.expected_roi:.0f}%</span>
                </div>
                <div class="summary-item">
                    <span class="label">Confidence:</span>
                    <span class="value">{strategy.confidence}</span>
                </div>
            </div>
            
            <div class="bracket-links">
                <strong>Direct Links:</strong>
                <ul>{links_html}</ul>
            </div>
            
            <div class="bracket-footer">
                {strategy.resolution_info}
            </div>
        </div>
        """
    
    @staticmethod
    def get_bracket_css() -> str:
        """Return CSS for bracket strategy styling"""
        return """
        .bracket-strategy {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 25px;
            margin: 25px 0;
            color: white;
        }
        
        .bracket-header h3 {
            font-size: 18px;
            margin-bottom: 5px;
        }
        
        .bracket-topic {
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 15px;
        }
        
        .bracket-thesis {
            background: rgba(255,255,255,0.15);
            padding: 12px 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        
        .bracket-trades h4 {
            font-size: 14px;
            margin-bottom: 12px;
        }
        
        .bracket-trade {
            display: flex;
            align-items: center;
            gap: 15px;
            background: rgba(255,255,255,0.1);
            padding: 10px 15px;
            border-radius: 6px;
            margin-bottom: 8px;
        }
        
        .bracket-label {
            font-weight: 600;
            min-width: 100px;
        }
        
        .bracket-action {
            flex: 1;
        }
        
        .bracket-edge {
            min-width: 120px;
        }
        
        .bracket-strategy .trade-link {
            background: white;
            color: #667eea !important;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            text-decoration: none;
        }
        
        .bracket-strategy .trade-link:hover {
            background: #f0f0f0;
        }
        
        .bracket-summary {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin: 20px 0;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
        }
        
        .summary-item {
            text-align: center;
        }
        
        .summary-item .label {
            font-size: 11px;
            text-transform: uppercase;
            opacity: 0.8;
            display: block;
        }
        
        .summary-item .value {
            font-size: 20px;
            font-weight: 700;
        }
        
        .bracket-strategy .edge-positive {
            color: #34d399;
        }
        
        .bracket-links {
            margin-top: 15px;
            font-size: 13px;
        }
        
        .bracket-links ul {
            list-style: none;
            padding: 0;
            margin-top: 8px;
        }
        
        .bracket-links li {
            margin-bottom: 5px;
        }
        
        .bracket-links a {
            color: #90cdf4;
        }
        
        .bracket-footer {
            text-align: center;
            margin-top: 15px;
            font-size: 12px;
            opacity: 0.8;
        }
        """


def detect_and_generate_bracket_strategies(
    markets: List[Market],
    model_forecasts: Optional[Dict[str, Dict[str, float]]] = None
) -> List[BracketStrategy]:
    """
    Convenience function to detect bracket groups and generate strategies.
    
    Args:
        markets: List of markets to analyze
        model_forecasts: Optional dict mapping topic -> {bracket_label: probability}
    
    Returns:
        List of BracketStrategy objects
    """
    detector = BracketDetector()
    generator = BracketStrategyGenerator(detector)
    
    # Group markets by topic
    groups = detector.group_related_markets(markets)
    
    strategies = []
    for topic, brackets in groups.items():
        forecasts = model_forecasts.get(topic) if model_forecasts else None
        strategy = generator.generate_strategy(topic, brackets, forecasts)
        if strategy:
            strategies.append(strategy)
    
    return strategies
