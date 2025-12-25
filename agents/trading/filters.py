"""
Market Selection Filters
Implements strict filtering criteria for trade candidates.
Includes EOY mode for end-of-year markets with relaxed thresholds.
"""
import logging
import re
from typing import List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from agents.trading.api_client import Market

logger = logging.getLogger(__name__)

# Category whitelist for EOY mode - prioritize these
EOY_PRIORITY_CATEGORIES = ['Politics', 'Crypto', 'Sports', 'Economics', 'AI', 'Tech']

# Keywords to infer categories from questions
CATEGORY_KEYWORDS = {
    'Politics': ['trump', 'biden', 'election', 'president', 'congress', 'senate', 'governor', 'vote', 'political', 'democrat', 'republican', 'cabinet', 'secretary'],
    'Crypto': ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'token', 'blockchain', 'usdc', 'usdt', 'tether', 'solana', 'doge'],
    'Sports': ['nfl', 'nba', 'mlb', 'super bowl', 'championship', 'world series', 'playoffs', 'mvp', 'game', 'match', 'team'],
    'Economics': ['recession', 'gdp', 'inflation', 'fed', 'interest rate', 'unemployment', 'stock', 'market', 's&p', 'dow', 'nasdaq'],
    'AI': ['ai', 'gpt', 'openai', 'anthropic', 'google ai', 'gemini', 'chatgpt', 'llm', 'model', 'artificial intelligence'],
    'Tech': ['apple', 'google', 'microsoft', 'nvidia', 'meta', 'amazon', 'tesla', 'ceo', 'ipo', 'acquisition']
}


def infer_category(question: str) -> Optional[str]:
    """Infer category from question text using keyword matching"""
    q_lower = question.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in q_lower:
                return category
    return None


@dataclass
class FilterConfig:
    """Configuration for market filters"""
    # Volume requirements
    min_total_volume: float = 150_000  # $150k minimum total volume
    min_volume_24h: float = 10_000     # $10k minimum 24h volume
    
    # Time requirements
    min_days_to_resolution: int = 30    # At least 30 days
    max_days_to_resolution: int = 180   # Not more than 6 months out
    
    # Price requirements
    max_high_outcome_price: float = 0.90  # Exclude if highest price > 90%
    min_low_outcome_price: float = 0.05   # Exclude if lowest price < 5%
    
    # Category filters (optional)
    excluded_categories: List[str] = None
    included_categories: List[str] = None
    
    # EOY mode specific
    eoy_mode: bool = False
    priority_categories: List[str] = None


class MarketFilter:
    """
    Applies strict filtering criteria to select tradeable markets.
    Logs all rejections with reasons.
    Supports EOY mode with category prioritization and near-miss tracking.
    """
    
    def __init__(self, config: Optional[FilterConfig] = None):
        self.config = config or FilterConfig()
        self.rejection_log: List[dict] = []
        self.near_misses: List[dict] = []  # Track markets that almost passed
    
    def filter_markets(self, markets: List[Market]) -> List[Market]:
        """
        Apply all filters to a list of markets.
        
        Returns:
            List of markets that pass all filters
        """
        self.rejection_log = []
        self.near_misses = []
        passed = []
        
        for market in markets:
            rejection_reason, near_miss_score = self._check_market(market)
            if rejection_reason:
                self._log_rejection(market, rejection_reason, near_miss_score)
            else:
                passed.append(market)
        
        # Sort near-misses by score (higher = closer to passing)
        self.near_misses = sorted(self.near_misses, key=lambda x: -x.get('score', 0))[:5]
        
        logger.info(f"Market filtering: {len(passed)}/{len(markets)} passed")
        self._print_rejection_summary()
        
        return passed
    
    def _check_market(self, market: Market) -> Tuple[Optional[str], float]:
        """
        Check if market passes all filters.
        
        Returns:
            Tuple of (rejection reason string or None, near-miss score 0-100)
        """
        score = 100.0  # Start with perfect score, deduct for failures
        
        # Check if market is closed
        if market.closed:
            return ("Market is closed", 0)
        
        # Check if market is active
        if not market.active:
            return ("Market is not active", 0)
        
        # Check total volume
        if market.volume < self.config.min_total_volume:
            # Calculate how close to passing
            vol_ratio = market.volume / self.config.min_total_volume
            score = score * vol_ratio
            return (f"Low total volume: ${market.volume:,.0f} < ${self.config.min_total_volume:,.0f}", score)
        
        # Check 24h volume
        if market.volume_24h < self.config.min_volume_24h:
            vol_ratio = market.volume_24h / self.config.min_volume_24h if self.config.min_volume_24h > 0 else 0
            score = score * max(vol_ratio, 0.5)  # Don't penalize too much
            return (f"Low 24h volume: ${market.volume_24h:,.0f} < ${self.config.min_volume_24h:,.0f}", score)
        
        # Check days to resolution
        days = market.days_to_resolution
        if days is None:
            return ("No resolution date", 0)
        
        if days < self.config.min_days_to_resolution:
            # Near-term markets in EOY mode get higher score
            if self.config.eoy_mode and days >= 1:
                score = score * 0.9  # Small penalty
            else:
                score = score * 0.5
            return (f"Too close to resolution: {days} days < {self.config.min_days_to_resolution} days", score)
        
        if days > self.config.max_days_to_resolution:
            return (f"Too far from resolution: {days} days > {self.config.max_days_to_resolution} days", score * 0.3)
        
        # Check price constraints (avoid near-certain outcomes)
        max_price = max(market.outcome_prices)
        min_price = min(market.outcome_prices)
        
        if max_price > self.config.max_high_outcome_price:
            # Calculate how certain - markets closer to 0.95 score better than 0.99
            certainty_penalty = (max_price - self.config.max_high_outcome_price) / (1 - self.config.max_high_outcome_price)
            score = score * (1 - certainty_penalty * 0.5)
            return (f"Outcome too certain: highest price ${max_price:.2f} > ${self.config.max_high_outcome_price:.2f}", score)
        
        if min_price < self.config.min_low_outcome_price:
            return (f"Outcome too unlikely: lowest price ${min_price:.2f} < ${self.config.min_low_outcome_price:.2f}", score * 0.4)
        
        # EOY mode: Boost score for priority categories
        if self.config.eoy_mode and self.config.priority_categories:
            category = infer_category(market.question)
            if category and category in self.config.priority_categories:
                score = min(score * 1.2, 100)  # Boost priority category markets
        
        # All checks passed
        return (None, score)
    
    def _log_rejection(self, market: Market, reason: str, near_miss_score: float = 0):
        """Log rejected market with reason"""
        entry = {
            "market_id": market.id,
            "question": market.question[:60] + "..." if len(market.question) > 60 else market.question,
            "reason": reason,
            "volume": market.volume,
            "volume_24h": market.volume_24h,
            "days_to_resolution": market.days_to_resolution,
            "prices": market.outcome_prices,
            "score": near_miss_score,
            "category": infer_category(market.question),
            "url": market.market_url,
            "slug": getattr(market, 'slug', None)
        }
        self.rejection_log.append(entry)
        
        # Track near-misses (score > 40 means it was close)
        if near_miss_score > 40:
            self.near_misses.append(entry)
    
    def _print_rejection_summary(self):
        """Print summary of rejection reasons"""
        if not self.rejection_log:
            return
        
        reasons = {}
        for item in self.rejection_log:
            reason_type = item["reason"].split(":")[0]
            reasons[reason_type] = reasons.get(reason_type, 0) + 1
        
        logger.info("Rejection summary:")
        for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
            logger.info(f"  - {reason}: {count}")
    
    def get_rejection_log(self) -> List[dict]:
        """Get full rejection log"""
        return self.rejection_log
    
    def get_near_misses(self) -> List[dict]:
        """Get top 5 markets that almost passed filters"""
        return self.near_misses


def get_relaxed_config() -> FilterConfig:
    """
    EOY Relaxed Mode - Per FIXES_COMPLETE.md spec:
    - Min days to resolution: 1 (allow near-term for EOY)
    - Min total volume: $50,000
    - Min 24h volume: $2,000
    - Allow outcomes up to $0.95
    - Priority categories enabled
    """
    return FilterConfig(
        min_total_volume=50_000,      # Down from $150k
        min_volume_24h=2_000,         # Down from $10k
        min_days_to_resolution=1,     # Allow near-term for EOY
        max_days_to_resolution=365,   # Allow longer term too
        max_high_outcome_price=0.95,  # Allow slight upside
        min_low_outcome_price=0.02,
        eoy_mode=True,
        priority_categories=EOY_PRIORITY_CATEGORIES
    )


def get_eoy_config() -> FilterConfig:
    """
    EOY-specific config - Focus on markets resolving by Jan 15, 2026
    Even more relaxed for end-of-year trading
    """
    return FilterConfig(
        min_total_volume=25_000,      # Lower for EOY liquidity
        min_volume_24h=500,           # Just needs some activity
        min_days_to_resolution=1,     # Allow very near-term
        max_days_to_resolution=30,    # Focus on EOY markets
        max_high_outcome_price=0.95,
        min_low_outcome_price=0.02,
        eoy_mode=True,
        priority_categories=EOY_PRIORITY_CATEGORIES
    )


def get_test_config() -> FilterConfig:
    """Get very relaxed test config (end of year edge case)"""
    return FilterConfig(
        min_total_volume=10_000,       # $10k total
        min_volume_24h=100,            # $100 24h
        min_days_to_resolution=1,      # Allow short-term
        max_days_to_resolution=365,
        max_high_outcome_price=0.98,   # Only skip if >98%
        min_low_outcome_price=0.01,
        eoy_mode=True,
        priority_categories=EOY_PRIORITY_CATEGORIES
    )


# Keep these for backwards compatibility
RelaxedFilterConfig = get_relaxed_config
TestFilterConfig = get_test_config
EOYFilterConfig = get_eoy_config
