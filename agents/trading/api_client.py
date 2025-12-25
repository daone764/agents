"""
Polymarket API Client
Direct API calls to Polymarket's official API endpoints.
Supports pagination, binary-only filtering, and fallback data.
"""
import requests
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, validator
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration - Use gamma API as primary
POLYMARKET_API_BASE = "https://gamma-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"

# Fallback sample markets for testing when API fails
FALLBACK_MARKETS = [
    {
        "id": "fallback_1",
        "question": "Will Bitcoin reach $150,000 by end of 2025?",
        "description": "Sample market for testing",
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.35", "0.65"],
        "volume": 500000,
        "volume24hr": 15000,
        "endDate": "2025-12-31T23:59:59Z",
        "closed": False,
        "active": True,
        "slug": "btc-150k-2025"
    },
    {
        "id": "fallback_2", 
        "question": "Will there be a US recession in 2025?",
        "description": "Sample market for testing",
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.25", "0.75"],
        "volume": 800000,
        "volume24hr": 20000,
        "endDate": "2025-12-31T23:59:59Z",
        "closed": False,
        "active": True,
        "slug": "us-recession-2025"
    },
    {
        "id": "fallback_3",
        "question": "Will NVIDIA remain the largest company by market cap on Jan 1, 2026?",
        "description": "Sample market for testing",
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.60", "0.40"],
        "volume": 300000,
        "volume24hr": 8000,
        "endDate": "2026-01-01T23:59:59Z",
        "closed": False,
        "active": True,
        "slug": "nvidia-largest-2026"
    }
]


class MarketOutcome(BaseModel):
    """Validated market outcome data"""
    name: str
    price: float = Field(ge=0, le=1)
    
    
class Market(BaseModel):
    """Validated market data from Polymarket API"""
    id: str
    question: str
    description: str = ""
    outcomes: List[str]
    outcome_prices: List[float]
    volume: float = 0
    volume_24h: float = 0
    end_date: Optional[datetime] = None
    closed: bool = False
    active: bool = True
    slug: str = ""
    
    @validator('outcome_prices', pre=True)
    def parse_prices(cls, v):
        if isinstance(v, str):
            import ast
            return [float(x) for x in ast.literal_eval(v)]
        return [float(x) for x in v]
    
    @validator('outcomes', pre=True)
    def parse_outcomes(cls, v):
        if isinstance(v, str):
            import ast
            return ast.literal_eval(v)
        return v
    
    @property
    def yes_price(self) -> float:
        return self.outcome_prices[0] if len(self.outcome_prices) > 0 else 0
    
    @property
    def no_price(self) -> float:
        return self.outcome_prices[1] if len(self.outcome_prices) > 1 else 0
    
    @property
    def days_to_resolution(self) -> Optional[int]:
        """Calculate days to resolution accurately using UTC"""
        if self.end_date:
            now = datetime.now(timezone.utc)
            # Ensure end_date is timezone-aware
            end = self.end_date if self.end_date.tzinfo else self.end_date.replace(tzinfo=timezone.utc)
            delta = end - now
            return max(0, delta.days)
        return None
    
    @property
    def is_binary(self) -> bool:
        """Check if market is binary (Yes/No only)"""
        if len(self.outcomes) != 2:
            return False
        outcomes_lower = [o.lower() for o in self.outcomes]
        return 'yes' in outcomes_lower and 'no' in outcomes_lower
    
    @property
    def market_url(self) -> str:
        """Generate Polymarket search URL for this market.
        
        Note: Individual market slugs may lead to 404 for multi-outcome events
        (e.g., tariff revenue buckets). Using search URL is more reliable.
        """
        # URL-encode the question for search
        import urllib.parse
        query = urllib.parse.quote(self.question[:60])
        return f"https://polymarket.com/markets?_q={query}"


class PolymarketAPIClient:
    """
    Client for Polymarket's official API.
    Handles rate limiting, retries, pagination, and data validation.
    Supports binary-only filtering and fallback markets.
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0, binary_only: bool = True):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "PolymarketTrader/1.0"
        })
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.binary_only = binary_only  # Only fetch Yes/No markets
        self.skipped_markets: List[Dict[str, Any]] = []
        self.use_fallback = False
    
    def _request(self, method: str, url: str, **kwargs) -> Optional[Dict]:
        """Make HTTP request with retry logic"""
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(method, url, timeout=30, **kwargs)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"All retries failed for {url}")
                    return None
        return None
    
    def get_active_markets(self, limit: int = 100, offset: int = 0) -> List[Market]:
        """
        Fetch active markets from Polymarket API.
        
        Returns:
            List of validated Market objects
        """
        url = f"{POLYMARKET_API_BASE}/markets"
        params = {
            "limit": limit,
            "offset": offset,
            "active": "true",
            "closed": "false"
        }
        
        data = self._request("GET", url, params=params)
        if not data:
            logger.error("Failed to fetch markets")
            return []
        
        markets = []
        for item in data:
            try:
                market = self._parse_market(item)
                if market:
                    # Filter for binary markets only if enabled
                    if self.binary_only and not market.is_binary:
                        self._log_skipped(market.id, "Multi-outcome market (not binary)")
                        continue
                    markets.append(market)
            except Exception as e:
                self._log_skipped(item.get("id", "unknown"), f"Parse error: {e}")
        
        logger.info(f"Fetched {len(markets)} valid markets (skipped {len(self.skipped_markets)} invalid)")
        return markets
    
    def get_all_active_markets(self, max_markets: int = 500, sort_by_volume: bool = True) -> List[Market]:
        """
        Fetch all active markets with pagination.
        
        Args:
            max_markets: Maximum number of markets to fetch (default 500)
            sort_by_volume: If True, sort by 24h volume descending
            
        Returns:
            List of validated Market objects
        """
        all_markets = []
        offset = 0
        page_size = 100  # API typically allows 100 per page
        
        while len(all_markets) < max_markets:
            markets = self.get_active_markets(limit=page_size, offset=offset)
            
            if not markets:
                # API might have failed, try fallback
                if offset == 0:
                    logger.warning("API failed, using fallback markets for testing")
                    return self._get_fallback_markets()
                break
            
            all_markets.extend(markets)
            
            # Stop if we got less than page_size (no more pages)
            if len(markets) < page_size:
                break
                
            offset += page_size
            time.sleep(0.5)  # Rate limiting between pages
        
        # Sort by 24h volume if requested
        if sort_by_volume:
            all_markets.sort(key=lambda m: m.volume_24h, reverse=True)
        
        logger.info(f"Total markets fetched: {len(all_markets)}")
        return all_markets[:max_markets]
    
    def _get_fallback_markets(self) -> List[Market]:
        """Return fallback markets for testing when API fails"""
        self.use_fallback = True
        markets = []
        for item in FALLBACK_MARKETS:
            market = self._parse_market(item)
            if market:
                markets.append(market)
        logger.warning(f"Using {len(markets)} fallback markets for testing")
        return markets
    
    def get_market(self, market_id: str) -> Optional[Market]:
        """Fetch a single market by ID"""
        url = f"{POLYMARKET_API_BASE}/markets/{market_id}"
        data = self._request("GET", url)
        if data:
            return self._parse_market(data)
        return None
    
    def _parse_market(self, data: Dict) -> Optional[Market]:
        """Parse and validate market data"""
        try:
            # Extract end date
            end_date = None
            end_date_str = data.get("endDate") or data.get("end_date_iso")
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                except:
                    pass
            
            # Parse outcome prices
            outcome_prices = data.get("outcomePrices") or data.get("outcome_prices", [])
            if isinstance(outcome_prices, str):
                import ast
                outcome_prices = ast.literal_eval(outcome_prices)
            outcome_prices = [float(p) for p in outcome_prices]
            
            # Parse outcomes
            outcomes = data.get("outcomes", ["Yes", "No"])
            if isinstance(outcomes, str):
                import ast
                outcomes = ast.literal_eval(outcomes)
            
            market = Market(
                id=str(data.get("id", data.get("condition_id", ""))),
                question=data.get("question", ""),
                description=data.get("description", ""),
                outcomes=outcomes,
                outcome_prices=outcome_prices,
                volume=float(data.get("volume", 0) or 0),
                volume_24h=float(data.get("volume24hr", data.get("volume_24h", 0)) or 0),
                end_date=end_date,
                closed=data.get("closed", False),
                active=data.get("active", True),
                slug=data.get("slug", data.get("market_slug", ""))
            )
            
            # Validate essential fields
            if not market.question:
                self._log_skipped(market.id, "Missing question")
                return None
            if len(market.outcome_prices) < 2:
                self._log_skipped(market.id, "Missing outcome prices")
                return None
                
            return market
            
        except Exception as e:
            self._log_skipped(data.get("id", "unknown"), f"Validation error: {e}")
            return None
    
    def _log_skipped(self, market_id: str, reason: str):
        """Log skipped markets for debugging"""
        self.skipped_markets.append({
            "market_id": market_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        logger.debug(f"Skipped market {market_id}: {reason}")
    
    def get_skipped_summary(self) -> Dict[str, int]:
        """Get summary of skipped markets by reason"""
        summary = {}
        for item in self.skipped_markets:
            reason = item["reason"].split(":")[0]
            summary[reason] = summary.get(reason, 0) + 1
        return summary
    
    def clear_skipped(self):
        """Clear skipped markets log"""
        self.skipped_markets = []
