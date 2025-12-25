# Trading module - improved bot components
from agents.trading.api_client import PolymarketAPIClient, Market
from agents.trading.filters import MarketFilter, FilterConfig, RelaxedFilterConfig
from agents.trading.edge_model import EdgeDetector, EdgeConfig, EdgeAnalysis, TradeAction
from agents.trading.position_sizing import PositionSizer, PositionConfig, PositionRecommendation
from agents.trading.recommendation_generator import RecommendationGenerator
from agents.trading.improved_trader import ImprovedTrader

__all__ = [
    "PolymarketAPIClient",
    "Market",
    "MarketFilter",
    "FilterConfig",
    "RelaxedFilterConfig",
    "EdgeDetector",
    "EdgeConfig",
    "EdgeAnalysis",
    "TradeAction",
    "PositionSizer",
    "PositionConfig",
    "PositionRecommendation",
    "RecommendationGenerator",
    "ImprovedTrader",
]
