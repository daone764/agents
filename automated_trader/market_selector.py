"""
Market Selection Module
Filters markets based on volume, resolution date, and market type criteria
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from automated_trader import config

logger = logging.getLogger(__name__)


class MarketSelector:
    """Selects markets that meet trading criteria"""
    
    def __init__(self, gamma_client, polymarket_client):
        """
        Args:
            gamma_client: GammaMarketClient for market metadata
            polymarket_client: Polymarket client for order book data
        """
        self.gamma = gamma_client
        self.polymarket = polymarket_client
        
    def get_tradeable_markets(self) -> List[Dict[str, Any]]:
        """
        Get all markets that meet selection criteria
        
        Returns:
            List of market dictionaries with metadata and order book data
        """
        logger.info("Fetching all active markets...")
        
        # Get all active markets from Gamma API
        all_markets = self.gamma.get_markets(querystring_params={
            "active": True,
            "closed": False,
            "limit": 100
        })
        
        logger.info(f"Found {len(all_markets)} active markets, filtering...")
        logger.info("=" * 80)
        
        tradeable_markets = []
        rejected_count = 0
        
        logger.info(f"Found {len(all_markets)} active markets, filtering...")
        logger.info("=" * 80)
        
        tradeable_markets = []
        rejected_count = 0
        
        for market in all_markets:
            market_id = market.get('conditionId', 'unknown')
            question = market.get('question', 'Unknown')[:60]
            
            # Get market metadata for logging
            volume = float(market.get('volume', 0))
            volume_24h = float(market.get('volume24hr', 0))
            
            # Check criteria with detailed logging
            rejection_reasons = []
            
            if self._meets_criteria(market, rejection_reasons):
                # Check spread using market data (already calculated by Polymarket)
                spread = float(market.get('spread', 1.0))
                best_bid = float(market.get('bestBid', 0))
                best_ask = float(market.get('bestAsk', 0))
                
                # Market spread is already calculated correctly
                # Accept if spread <= threshold
                spread_ok = spread <= config.MAX_BID_ASK_SPREAD_PCT
                
                if not spread_ok:
                    rejected_count += 1
                    hours_result = self._get_hours_to_resolution(market)
                    hours_remaining = hours_result['hours'] if hours_result else 0
                    resolution_timestamp = hours_result['timestamp'] if hours_result else 'Unknown'
                    rejection_reasons.append(f"spread too wide: {spread:.2%}")
                    
                    logger.info(f"❌ REJECTED: {question}...")
                    logger.info(f"   Market ID: {market_id}")
                    logger.info(f"   Total Volume: ${volume:,.0f}")
                    logger.info(f"   24h Volume: ${volume_24h:,.0f}")
                    logger.info(f"   Resolution: {resolution_timestamp} ({hours_remaining:.1f} hours)")
                    logger.info(f"   Best Bid: {best_bid:.4f}, Best Ask: {best_ask:.4f}, Spread: {spread:.2%}")
                    logger.info(f"   Reason: {', '.join(rejection_reasons)}")
                    continue
                
                # Market passed all checks!
                tradeable_markets.append(market)
                
                # Log eligible market
                hours_result = self._get_hours_to_resolution(market)
                hours_remaining = hours_result['hours'] if hours_result else 0
                resolution_timestamp = hours_result['timestamp'] if hours_result else 'Unknown'
                logger.info(f"✅ ELIGIBLE: {question}...")
                logger.info(f"   Market ID: {market_id}")
                logger.info(f"   Total Volume: ${volume:,.0f}")
                logger.info(f"   24h Volume: ${volume_24h:,.0f}")
                logger.info(f"   Resolution: {resolution_timestamp} ({hours_remaining:.1f} hours, {hours_remaining/24:.1f} days)")
                logger.info(f"   Best Bid: {best_bid:.4f}, Best Ask: {best_ask:.4f}, Spread: {spread:.2%}")
                logger.info(f"   Status: PASS ✓")
            else:
                rejected_count += 1
                hours_result = self._get_hours_to_resolution(market)
                hours_remaining = hours_result['hours'] if hours_result else 0
                resolution_timestamp = hours_result['timestamp'] if hours_result else 'Unknown'
                logger.info(f"❌ REJECTED: {question}...")
                logger.info(f"   Market ID: {market_id}")
                logger.info(f"   Total Volume: ${volume:,.0f}")
                logger.info(f"   24h Volume: ${volume_24h:,.0f}")
                logger.info(f"   Resolution: {resolution_timestamp} ({hours_remaining:.1f} hours)")
                logger.info(f"   Reason: {', '.join(rejection_reasons)}")
        
        logger.info("=" * 80)
        logger.info(f"✓ {len(tradeable_markets)} markets ELIGIBLE, {rejected_count} REJECTED")
        return tradeable_markets
    
    def _meets_criteria(self, market: Dict[str, Any], rejection_reasons: List[str]) -> bool:
        """
        Check if market meets all selection criteria
        
        Args:
            market: Market metadata dictionary
            rejection_reasons: List to populate with rejection reasons
            
        Returns:
            True if market meets all criteria
        """
        # Check if binary Yes/No market
        if config.BINARY_ONLY:
            outcomes = market.get('outcomes', [])
            if not self._is_binary_market(outcomes):
                rejection_reasons.append("not binary Yes/No")
                return False
        
        # Check total volume
        volume = float(market.get('volume', 0))
        if volume < config.MIN_TOTAL_VOLUME:
            rejection_reasons.append(f"low volume: ${volume:,.0f} < ${config.MIN_TOTAL_VOLUME:,.0f}")
            return False
        
        # Check 24h volume
        volume_24h = float(market.get('volume24hr', 0))
        if volume_24h < config.MIN_24H_VOLUME:
            rejection_reasons.append(f"low 24h volume: ${volume_24h:,.0f} < ${config.MIN_24H_VOLUME:,.0f}")
            return False
        
        # Check hours to resolution (use precise UTC timestamp comparison)
        hours_result = self._get_hours_to_resolution(market)
        if hours_result is None:
            rejection_reasons.append("no end date")
            return False
        
        hours_remaining = hours_result['hours']
        if hours_remaining < config.MIN_HOURS_TO_RESOLUTION:
            rejection_reasons.append(f"too close to resolution: {hours_remaining:.1f} hours < {config.MIN_HOURS_TO_RESOLUTION} hours ({hours_remaining/24:.1f} days)")
            return False
        
        # Check for excluded keywords (breaking news, fast-moving)
        question = market.get('question', '').lower()
        description = market.get('description', '').lower()
        
        for keyword in config.EXCLUDED_KEYWORDS:
            if keyword.lower() in question or keyword.lower() in description:
                rejection_reasons.append(f"excluded keyword: '{keyword}'")
                return False
        
        return True
    
    def _is_binary_market(self, outcomes) -> bool:
        """Check if market is binary Yes/No"""
        # Handle outcomes as JSON string
        if isinstance(outcomes, str):
            import json
            try:
                outcomes = json.loads(outcomes)
            except:
                return False
        
        if len(outcomes) != 2:
            return False
        
        outcomes_lower = [o.lower() for o in outcomes]
        return 'yes' in outcomes_lower and 'no' in outcomes_lower
    
    def _check_bid_ask_spread(self, order_book: Dict[str, Any]) -> dict:
        """
        Check if bid-ask spread is acceptable (liquidity health gate)
        
        YES and NO are separate order books - do NOT compare across them.
        Market is acceptable if EITHER side has good spread (<= 8%).
        Reject only if BOTH sides have poor spread (> 8%).
        
        Args:
            order_book: Dict with 'yes' and 'no' order books
            
        Returns:
            Dict with keys: ok, yes_spread, no_spread, yes_bid, yes_ask, no_bid, no_ask
        """
        try:
            # Each side (yes/no) has its own order book with bids/asks
            yes_ob = order_book.get('yes', {})
            no_ob = order_book.get('no', {})
            
            yes_bids = yes_ob.get('bids', []) if isinstance(yes_ob, dict) else (yes_ob.bids if hasattr(yes_ob, 'bids') else [])
            yes_asks = yes_ob.get('asks', []) if isinstance(yes_ob, dict) else (yes_ob.asks if hasattr(yes_ob, 'asks') else [])
            no_bids = no_ob.get('bids', []) if isinstance(no_ob, dict) else (no_ob.bids if hasattr(no_ob, 'bids') else [])
            no_asks = no_ob.get('asks', []) if isinstance(no_ob, dict) else (no_ob.asks if hasattr(no_ob, 'asks') else [])
            
            # Need at least one bid and ask on each side
            if not (yes_bids and yes_asks and no_bids and no_asks):
                return {
                    'ok': False,
                    'yes_spread': 1.0,
                    'no_spread': 1.0,
                    'yes_bid': 0.0,
                    'yes_ask': 0.0,
                    'no_bid': 0.0,
                    'no_ask': 0.0
                }
            
            # Get best prices (bids/asks are OrderSummary objects)
            def get_price(order):
                if isinstance(order, dict):
                    return float(order.get('price', 0))
                return float(order.price) if hasattr(order, 'price') else 0
            
            yes_best_bid = get_price(yes_bids[0])
            yes_best_ask = get_price(yes_asks[0])
            no_best_bid = get_price(no_bids[0])
            no_best_ask = get_price(no_asks[0])
            
            # Calculate spread for each side using midpoint formula:
            # spread = (ask - bid) / ((ask + bid) / 2)
            # This gives percentage spread relative to midpoint
            def calc_spread(bid, ask):
                if bid <= 0 or ask <= 0:
                    return 1.0
                midpoint = (ask + bid) / 2.0
                if midpoint == 0:
                    return 1.0
                return (ask - bid) / midpoint
            
            yes_spread = calc_spread(yes_best_bid, yes_best_ask)
            no_spread = calc_spread(no_best_bid, no_best_ask)
            
            # Market is acceptable if at least one side has good spread
            # Reject ONLY if BOTH spreads exceed threshold
            min_spread = min(yes_spread, no_spread)
            spread_ok = min_spread <= config.MAX_BID_ASK_SPREAD_PCT
            
            return {
                'ok': spread_ok,
                'yes_spread': yes_spread,
                'no_spread': no_spread,
                'yes_bid': yes_best_bid,
                'yes_ask': yes_best_ask,
                'no_bid': no_best_bid,
                'no_ask': no_best_ask
            }
            
        except Exception as e:
            logger.warning(f"Failed to check bid-ask spread: {e}")
            return {
                'ok': False,
                'yes_spread': 1.0,
                'no_spread': 1.0,
                'yes_bid': 0.0,
                'yes_ask': 0.0,
                'no_bid': 0.0,
                'no_ask': 0.0
            }
    
    def _get_hours_to_resolution(self, market: Dict[str, Any]):
        """
        Get hours remaining until market resolution using precise UTC timestamps
        
        Args:
            market: Market metadata dictionary
            
        Returns:
            Dict with 'hours' and 'timestamp', or None if cannot be determined
        """
        end_date_str = market.get('endDateIso') or market.get('endDate')
        
        if not end_date_str:
            return None
        
        try:
            # Parse ISO format datetime to UTC
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            now_utc = datetime.now(end_date.tzinfo)
            
            # Calculate precise hours remaining
            time_delta = end_date - now_utc
            hours_remaining = time_delta.total_seconds() / 3600.0
            
            return {
                'hours': hours_remaining,
                'timestamp': end_date_str
            }
            
        except Exception as e:
            logger.debug(f"Failed to parse end date '{end_date_str}': {e}")
            return None
    
    def _has_sufficient_time(self, market: Dict[str, Any]) -> bool:
        """Check if market has enough time until resolution (legacy method)"""
        hours_result = self._get_hours_to_resolution(market)
        if hours_result is None:
            return False
        return hours_result['hours'] >= config.MIN_HOURS_TO_RESOLUTION
