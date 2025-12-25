"""
Improved Trading Bot - Main Orchestrator
Integrates all modules for safe, high-quality trade recommendations.
Supports EOY mode with relaxed filters for end-of-year markets.
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI

from agents.trading.api_client import PolymarketAPIClient, Market
from agents.trading.filters import MarketFilter, FilterConfig, get_relaxed_config, get_eoy_config, get_test_config
from agents.trading.edge_model import EdgeDetector, EdgeConfig, EdgeAnalysis, TradeAction, parse_model_probability, get_relaxed_edge_config
from agents.trading.position_sizing import PositionSizer, PositionConfig
from agents.trading.recommendation_generator import RecommendationGenerator
from agents.trading.email_sender import EmailSender
from agents.trading.bracket_strategy import BracketDetector, BracketStrategyGenerator, BracketStrategy
from agents.application.prompts import Prompter
from agents.connectors.search import tavily_client
from agents.connectors.news import News
from agents.polymarket.polymarket import Polymarket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Position tracking file
POSITIONS_FILE = "active_positions.json"
MAX_CONCURRENT_POSITIONS = 5


class PositionTracker:
    """Track concurrent positions to prevent over-trading"""
    
    def __init__(self, filepath: str = POSITIONS_FILE):
        self.filepath = Path(filepath)
        self.positions = self._load()
    
    def _load(self) -> Dict:
        if self.filepath.exists():
            try:
                with open(self.filepath, 'r') as f:
                    return json.load(f)
            except:
                return {"positions": [], "count": 0}
        return {"positions": [], "count": 0}
    
    def _save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.positions, f, indent=2, default=str)
    
    def can_add_position(self) -> bool:
        return self.positions["count"] < MAX_CONCURRENT_POSITIONS
    
    def add_position(self, market_id: str, question: str, action: str, amount: float):
        self.positions["positions"].append({
            "market_id": market_id,
            "question": question[:50],
            "action": action,
            "amount": amount,
            "timestamp": datetime.now().isoformat()
        })
        self.positions["count"] = len(self.positions["positions"])
        self._save()
    
    def get_count(self) -> int:
        return self.positions["count"]


class ImprovedTrader:
    """
    Improved trading bot with strict filters, edge detection, and safe sizing.
    Supports EOY mode with relaxed filters for end-of-year markets.
    """
    
    def __init__(self, mode: str = "strict"):
        """
        Initialize trader with specified mode.
        
        Args:
            mode: "strict", "relaxed", "eoy", or "test"
        """
        load_dotenv()
        self.mode = mode
        
        # Initialize API client with binary-only filter
        self.api_client = PolymarketAPIClient(binary_only=True)
        
        # Configure filters based on mode
        if mode == "test":
            filter_config = get_test_config()
            edge_config = get_relaxed_edge_config()
            logger.info("🔧 Using TEST filters (very relaxed)")
        elif mode == "eoy":
            filter_config = get_eoy_config()
            edge_config = get_relaxed_edge_config()
            logger.info("🎄 Using EOY mode - focus on markets resolving by Jan 15, 2026")
        elif mode == "relaxed":
            filter_config = get_relaxed_config()
            edge_config = get_relaxed_edge_config()
            logger.info("📊 Using RELAXED filters for EOY trading")
        else:
            filter_config = FilterConfig()
            edge_config = EdgeConfig()
            logger.info("🔒 Using STRICT filters for production")
        
        self.market_filter = MarketFilter(filter_config)
        self.edge_detector = EdgeDetector(edge_config)
        self.recommendation_gen = RecommendationGenerator()
        self.position_tracker = PositionTracker()
        
        # LLM for forecasting
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo-16k",
            temperature=0,
        )
        self.prompter = Prompter()
        self.news = News()
        
        # Portfolio state
        self.polymarket = Polymarket()
        self.bankroll = self.polymarket.get_usdc_balance()
        
        # Adjust position sizing based on bankroll size
        # Small bankrolls need larger % to meet minimum trade size
        if self.bankroll < 50:
            max_pos_pct = 5.0   # 5% max ($1.25 on $25)
            min_pos_usd = 0.50  # $0.50 minimum
        elif self.bankroll < 100:
            max_pos_pct = 3.0   # 3% max
            min_pos_usd = 0.50
        else:
            max_pos_pct = 1.0   # 1% max for larger bankrolls
            min_pos_usd = 1.00
        
        # Use conservative position sizing for EOY/relaxed modes
        if mode in ["eoy", "relaxed", "test"]:
            position_config = PositionConfig(
                max_position_percent=max_pos_pct,
                max_short_term_percent=max_pos_pct,
                max_concurrent_positions=MAX_CONCURRENT_POSITIONS,
                min_position_usd=min_pos_usd
            )
        else:
            position_config = PositionConfig()
        
        self.position_sizer = PositionSizer(
            bankroll=self.bankroll,
            current_positions=self.position_tracker.get_count(),
            deployed_capital=0,
            config=position_config
        )
        
        # Statistics
        self.markets_scanned = 0
        self.markets_passed_filter = 0
        self.trades_recommended = 0
        self.analyzed_markets: List[Dict] = []  # Track analyzed markets for summary
        self.bracket_strategies: List[BracketStrategy] = []  # Track bracket strategies
        
        # Bracket detector for combined strategies
        self.bracket_detector = BracketDetector()
        self.bracket_generator = BracketStrategyGenerator(self.bracket_detector)
    
    def run_analysis(self, max_markets: int = 500) -> List[str]:
        """
        Run full analysis pipeline.
        
        Args:
            max_markets: Maximum markets to fetch (default 500 with pagination)
        
        Returns:
            List of saved recommendation filenames
        """
        logger.info("=" * 60)
        logger.info("STARTING IMPROVED TRADER ANALYSIS")
        logger.info(f"Mode: {self.mode.upper()}")
        logger.info("=" * 60)
        logger.info(f"Bankroll: ${self.bankroll:.2f}")
        logger.info(f"Current positions: {self.position_tracker.get_count()}/{MAX_CONCURRENT_POSITIONS}")
        
        # Check if we can add more positions
        if not self.position_tracker.can_add_position():
            logger.warning(f"⚠️ Maximum positions ({MAX_CONCURRENT_POSITIONS}) reached!")
            no_trade = self.recommendation_gen.generate_no_trade(
                f"Maximum concurrent positions ({MAX_CONCURRENT_POSITIONS}) reached. Wait for current positions to resolve."
            )
            filename = self.recommendation_gen.save_recommendation(no_trade, "no_trade")
            return [filename]
        
        # Step 1: Fetch markets from API with pagination
        logger.info("\n📥 Fetching markets from Polymarket API...")
        markets = self.api_client.get_all_active_markets(max_markets=max_markets, sort_by_volume=True)
        self.markets_scanned = len(markets)
        logger.info(f"Fetched {self.markets_scanned} markets")
        
        if not markets:
            logger.error("No markets retrieved from API")
            return []
        
        # Step 2: Apply filters
        logger.info("\n🔍 Applying market filters...")
        filtered_markets = self.market_filter.filter_markets(markets)
        self.markets_passed_filter = len(filtered_markets)
        logger.info(f"{self.markets_passed_filter} markets passed filters")
        
        # Get near-misses for output
        near_misses = self.market_filter.get_near_misses()
        
        if not filtered_markets:
            logger.warning("No markets passed filters")
            no_trade = self.recommendation_gen.generate_no_trade(
                "No markets passed quality filters. See near-miss suggestions below.",
                near_misses=near_misses
            )
            filename = self.recommendation_gen.save_recommendation(no_trade, "no_trade")
            return [filename]
        
        # Step 3: Analyze each market for edge
        logger.info("\n📊 Analyzing markets for trading edge...")
        recommendations = []
        
        for market in filtered_markets[:10]:  # Analyze top 10 by volume
            rec_file = self._analyze_market(market)
            if rec_file:
                recommendations.append(rec_file)
                self.trades_recommended += 1
                
                # Stop if we hit max positions
                if not self.position_tracker.can_add_position():
                    logger.info("Reached maximum concurrent positions")
                    break
        
        # Step 3.5: Detect bracket strategies (combined bets on related markets)
        logger.info("\n📊 Detecting bracket strategies...")
        self._detect_bracket_strategies(markets)
        
        # Step 4: Generate summary (both text and HTML)
        logger.info("\n📋 Generating daily summary...")
        
        # Text summary for console/logs
        summary = self.recommendation_gen.generate_daily_summary(
            markets_scanned=self.markets_scanned,
            markets_valid=self.markets_passed_filter,
            trades_recommended=self.trades_recommended,
            rejections_by_reason=self._get_all_rejections(),
            near_misses=near_misses,
            analyzed_markets=self.analyzed_markets,
            bracket_strategies=self.bracket_strategies
        )
        summary_file = self.recommendation_gen.save_recommendation(summary, "daily_summary")
        
        # HTML report (pretty version)
        html_report = self.recommendation_gen.generate_html_summary(
            markets_scanned=self.markets_scanned,
            markets_valid=self.markets_passed_filter,
            trades_recommended=self.trades_recommended,
            rejections_by_reason=self._get_all_rejections(),
            near_misses=near_misses,
            analyzed_markets=self.analyzed_markets,
            bracket_strategies=self.bracket_strategies
        )
        html_file = self.recommendation_gen.save_html(html_report, "trading_report")
        logger.info(f"📄 HTML report saved: {html_file}")
        
        # Email report if configured
        email_sender = EmailSender()
        if email_sender.is_configured():
            logger.info("📧 Sending email report...")
            if email_sender.send_html_report(html_report, attach_file=html_file):
                logger.info("✅ Email sent successfully!")
            else:
                logger.warning("❌ Failed to send email")
        else:
            logger.info("📧 Email not configured - skipping (set GMAIL_APP_PASSWORD in .env)")
        
        logger.info(f"\n✅ Analysis complete!")
        logger.info(f"   Markets scanned: {self.markets_scanned}")
        logger.info(f"   Markets passed filters: {self.markets_passed_filter}")
        logger.info(f"   Trades recommended: {self.trades_recommended}")
        
        return recommendations
    
    def _analyze_market(self, market: Market) -> Optional[str]:
        """Analyze a single market for trading opportunity"""
        logger.info(f"\n--- Analyzing: {market.question[:60]}...")
        
        try:
            # Get real-time context
            context = self._gather_context(market.question)
            
            # Get LLM forecast
            model_prob, outcome = self._get_llm_forecast(market, context)
            
            if model_prob is None:
                logger.warning(f"Could not parse LLM probability for market {market.id}")
                # Use 50% as fallback (per FIXES_COMPLETE.md spec)
                model_prob = 0.5
                outcome = "Yes"
                logger.info("Using 50% as fallback probability")
            
            # Convert to YES probability
            if outcome and outcome.lower() == "no":
                yes_prob = 1 - model_prob
            else:
                yes_prob = model_prob
            
            logger.info(f"Model forecast: {yes_prob*100:.1f}% YES, {(1-yes_prob)*100:.1f}% NO")
            logger.info(f"Market prices: ${market.yes_price:.4f} YES, ${market.no_price:.4f} NO")
            
            # Detect edge
            analysis = self.edge_detector.analyze_edge(market, yes_prob)
            logger.info(f"Edge analysis: {analysis.reason}")
            
            # Track for summary
            self.analyzed_markets.append({
                "question": market.question,
                "model_prob": yes_prob,
                "market_price": market.yes_price,
                "edge": analysis.edge_percent,
                "action": analysis.recommended_action.value,
                "url": market.market_url,
                "slug": getattr(market, 'slug', None)
            })
            
            if not analysis.meets_threshold:
                return None
            
            # Calculate position size
            position = self.position_sizer.calculate_position(analysis)
            logger.info(f"Position sizing: {position.reason}")
            
            if not position.should_trade:
                return None
            
            # Generate recommendation
            recommendation = self.recommendation_gen.generate(
                analysis=analysis,
                position=position,
                bankroll=self.bankroll
            )
            
            # Save and return
            filename = self.recommendation_gen.save_recommendation(recommendation)
            logger.info(f"✅ Trade recommended! Saved to: {filename}")
            
            # Track position (but don't actually execute - user does manually)
            self.position_tracker.add_position(
                market_id=market.id,
                question=market.question,
                action=analysis.recommended_action.value,
                amount=position.position_usd
            )
            
            # Print recommendation
            print(recommendation)
            
            return filename
            
        except Exception as e:
            logger.error(f"Error analyzing market {market.id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _gather_context(self, question: str) -> str:
        """Gather real-time context for forecasting"""
        context = ""
        
        try:
            search_results = tavily_client.get_search_context(query=question, max_results=5)
            context += f"\n**Web Search:**\n{search_results}\n"
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}")
        
        try:
            articles = self.news.get_articles_for_options([question])
            if articles:
                context += "\n**Recent News:**\n"
                for keyword, arts in articles.items():
                    for art in arts[:2]:
                        context += f"- {art.get('title', '')}\n"
        except Exception as e:
            logger.warning(f"News API failed: {e}")
        
        return context
    
    def _get_llm_forecast(self, market: Market, context: str) -> tuple:
        """Get probability forecast from LLM"""
        prompt = self.prompter.superforecaster(
            question=market.question,
            description=market.description,
            outcome=market.outcomes,
            realtime_context=context
        )
        
        result = self.llm.invoke(prompt)
        response = result.content
        
        logger.debug(f"LLM response: {response[:200]}...")
        
        return parse_model_probability(response)
    
    def _detect_bracket_strategies(self, markets: List[Market]):
        """Detect and generate bracket strategies for related markets"""
        try:
            # Group markets by topic
            bracket_groups = self.bracket_detector.group_related_markets(markets)
            
            if not bracket_groups:
                logger.info("No bracket market groups detected")
                return
            
            logger.info(f"Found {len(bracket_groups)} potential bracket groups")
            
            for topic, brackets in bracket_groups.items():
                logger.info(f"  - {topic}: {len(brackets)} brackets")
                
                # Build model forecasts from analyzed markets
                model_forecasts = {}
                for bracket in brackets:
                    # Try to find matching analyzed market
                    for am in self.analyzed_markets:
                        if am.get('question', '').startswith(bracket.market.question[:30]):
                            model_forecasts[bracket.bracket_label] = am.get('model_prob', bracket.yes_price)
                            break
                
                # Generate strategy
                strategy = self.bracket_generator.generate_strategy(topic, brackets, model_forecasts)
                
                if strategy and strategy.recommended_trades:
                    self.bracket_strategies.append(strategy)
                    logger.info(f"✅ Bracket strategy generated for: {topic}")
                    
                    # Print text summary to console
                    print(self.bracket_generator.format_strategy_text(strategy))
            
        except Exception as e:
            logger.warning(f"Bracket detection failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_all_rejections(self) -> dict:
        """Combine all rejection reasons"""
        rejections = {}
        
        # From API client
        for reason, count in self.api_client.get_skipped_summary().items():
            rejections[f"API: {reason}"] = count
        
        # From filter
        filter_reasons = {}
        for item in self.market_filter.get_rejection_log():
            reason = item["reason"].split(":")[0]
            filter_reasons[f"Filter: {reason}"] = filter_reasons.get(f"Filter: {reason}", 0) + 1
        rejections.update(filter_reasons)
        
        return rejections


def main():
    """Run the improved trader"""
    import sys
    
    # Parse command line flags
    args = sys.argv[1:]
    
    # Determine mode
    if "--eoy" in args:
        mode = "eoy"
    elif "--test" in args:
        mode = "test"
    elif "--relaxed" in args:
        mode = "relaxed"
    else:
        mode = "strict"
    
    print(f"""
================================================================================
                     POLYMARKET IMPROVED TRADER
================================================================================
Mode: {mode.upper()}
Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}

Usage:
  python improved_trader.py             # Strict mode (production)
  python improved_trader.py --relaxed   # Relaxed filters for EOY markets
  python improved_trader.py --eoy       # EOY mode (markets by Jan 15, 2026)
  python improved_trader.py --test      # Test mode (very relaxed)
================================================================================
""")
    
    trader = ImprovedTrader(mode=mode)
    recommendations = trader.run_analysis()
    
    # Print summary table
    print(f"\n{'='*100}")
    print("                              ANALYSIS SUMMARY")
    print(f"{'='*100}")
    
    if trader.analyzed_markets:
        # Header
        print(f"\n+{'-'*50}+{'-'*8}+{'-'*8}+{'-'*8}+{'-'*18}+")
        print(f"| {'MARKET':<48} | {'MODEL':>6} | {'PRICE':>6} | {'EDGE':>6} | {'ACTION':<16} |")
        print(f"+{'-'*50}+{'-'*8}+{'-'*8}+{'-'*8}+{'-'*18}+")
        
        for am in trader.analyzed_markets:
            action = am.get('action', 'NO_TRADE')
            question = am.get('question', 'Unknown')[:47]
            model_pct = am.get('model_prob', 0) * 100
            market_pct = am.get('market_price', 0) * 100
            edge = am.get('edge', 0)
            
            # Highlight trades
            if action in ('BUY_YES', 'BUY_NO'):
                marker = ">>>"
                action_str = f"*** {action} ***"
            else:
                marker = "   "
                action_str = action
            
            print(f"|{marker}{question:<47} | {model_pct:>5.0f}% | {market_pct:>5.0f}% | {edge:>+5.1f}% | {action_str:<16} |")
        
        print(f"+{'-'*50}+{'-'*8}+{'-'*8}+{'-'*8}+{'-'*18}+")
    
    # Show recommended trades with clickable links
    recommended = [am for am in trader.analyzed_markets if am.get('action') in ('BUY_YES', 'BUY_NO')]
    if recommended:
        print(f"\n{'*'*100}")
        print("                    >>> RECOMMENDED TRADES - EXECUTE ON POLYMARKET <<<")
        print(f"{'*'*100}")
        for i, am in enumerate(recommended, 1):
            url = am.get('url', 'https://polymarket.com')
            print(f"\n  [{i}] {am.get('question', 'Unknown')[:70]}")
            print(f"      ACTION: {am.get('action')} | Edge: {am.get('edge', 0):+.1f}%")
            print(f"      TRADE LINK: {url}")
        print(f"\n{'*'*100}")
        print(f"\nTotal: {len(recommendations)} trade recommendations generated.")
        print("Open trading_report_*.html in browser for pretty formatted report!")
    else:
        print("\nNo strong trade recommendations at this time.")
        print("Check the daily_summary file for near-miss markets to review manually.")
    
    print(f"\nFiles generated: trading_report_*.html (pretty) | daily_summary_*.txt (text)")
    print(f"{'='*100}")


if __name__ == "__main__":
    main()
