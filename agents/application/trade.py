from agents.application.executor import Executor as Agent
from agents.polymarket.gamma import GammaMarketClient as Gamma
from agents.polymarket.polymarket import Polymarket

import shutil
import json
import re
from datetime import datetime
import random


class Trader:
    def __init__(self):
        self.polymarket = Polymarket()
        self.gamma = Gamma()
        self.agent = Agent()

    def pre_trade_logic(self) -> None:
        self.clear_local_dbs()

    def clear_local_dbs(self) -> None:
        try:
            shutil.rmtree("local_db_events")
        except:
            pass
        try:
            shutil.rmtree("local_db_markets")
        except:
            pass

    def get_multiple_recommendations(self, num_recommendations: int = 10, execute: bool = False, max_retries: int = 3, retry_count: int = 0) -> list:
        """
        Get multiple trade recommendations for diversification
        
        Args:
            num_recommendations: Number of recommendations to generate (default 10)
            execute: Whether to execute trades (default False)
        
        Returns:
            List of trade recommendation dictionaries
        """
        try:
            self.pre_trade_logic()

            events = self.polymarket.get_all_tradeable_events()
            print(f"1. FOUND {len(events)} EVENTS")

            filtered_events = self.agent.filter_events_with_rag(events)
            print(f"2. FILTERED {len(filtered_events)} EVENTS")

            markets = self.agent.map_filtered_events_to_markets(filtered_events)
            print(f"3. FOUND {len(markets)} MARKETS")

            filtered_markets = self.agent.filter_markets(markets)
            print(f"4. FILTERED {len(filtered_markets)} MARKETS")
            
            # Get multiple recommendations
            recommendations = []
            seen_questions = set()  # Track unique markets by question
            num_to_process = min(num_recommendations, len(filtered_markets))
            
            market_idx = 0
            attempts = 0
            max_attempts = len(filtered_markets)
            
            while len(recommendations) < num_to_process and attempts < max_attempts:
                if market_idx >= len(filtered_markets):
                    print(f"\n⚠️ Only {len(recommendations)} unique markets available")
                    break
                
                market = filtered_markets[market_idx]
                market_idx += 1
                attempts += 1
                
                # Extract market question for deduplication
                try:
                    market_doc = market[0].dict()
                    market_question = market_doc["metadata"]["question"]
                    
                    # Skip if we've already seen this market
                    if market_question in seen_questions:
                        print(f"  ⏭️ Skipping duplicate market: {market_question[:50]}...")
                        continue
                    
                    seen_questions.add(market_question)
                    
                except Exception as e:
                    print(f"  ⚠️ Could not extract market question: {e}")
                    continue
                
                print(f"\n🔍 Analyzing market {len(recommendations)+1}/{num_to_process}...")
                print(f"   {market_question[:80]}...")
                
                best_trade = self.agent.source_best_trade(market)
                
                # Parse trade recommendation
                trade_data = self._parse_trade_recommendation(best_trade, market)
                amount = self.agent.format_trade_prompt_for_execution(best_trade)
                trade_data["amount_usdc"] = amount
                
                recommendations.append(trade_data)
            
            # Remove any remaining duplicates based on market question
            unique_recommendations = []
            seen_final = set()
            for rec in recommendations:
                question = rec.get('market', {}).get('question', '')
                if question and question not in seen_final:
                    seen_final.add(question)
                    unique_recommendations.append(rec)
            
            # Save all recommendations to a single file
            self._save_multiple_recommendations(unique_recommendations, execute)
            
            print(f"\n✅ Generated {len(unique_recommendations)} unique recommendations")
            return unique_recommendations
            
        except Exception as e:
            if retry_count < max_retries:
                print(f"Error {e} \n \n Retrying ({retry_count + 1}/{max_retries})...")
                return self.get_multiple_recommendations(num_recommendations=num_recommendations, execute=execute, max_retries=max_retries, retry_count=retry_count + 1)
            else:
                print(f"Failed after {max_retries} attempts. Last error: {e}")
                raise
    
    def get_recommendation_for_market(self, market, execute: bool = False) -> dict:
        """
        Get AI recommendation for a specific market selected by user
        
        Args:
            market: Market document from agent.map_filtered_events_to_markets
            execute: Whether to execute the trade
            
        Returns:
            Trade recommendation dictionary
        """
        try:
            print(f"\n🔍 Analyzing selected market...")
            best_trade = self.agent.source_best_trade(market)
            
            # Parse trade recommendation
            trade_data = self._parse_trade_recommendation(best_trade, market)
            amount = self.agent.format_trade_prompt_for_execution(best_trade)
            trade_data["amount_usdc"] = amount
            
            # Save recommendation
            self._save_trade_recommendation(trade_data, execute)
            
            return trade_data
        except Exception as e:
            print(f"Error getting recommendation for market: {e}")
            raise
    
    def one_best_trade(self, execute: bool = False, max_retries: int = 3, retry_count: int = 0) -> None:
        """

        one_best_trade is a strategy that evaluates all events, markets, and orderbooks

        leverages all available information sources accessible to the autonomous agent

        then executes that trade without any human intervention

        """
        try:
            self.pre_trade_logic()

            events = self.polymarket.get_all_tradeable_events()
            print(f"1. FOUND {len(events)} EVENTS")

            filtered_events = self.agent.filter_events_with_rag(events)
            print(f"2. FILTERED {len(filtered_events)} EVENTS")

            markets = self.agent.map_filtered_events_to_markets(filtered_events)
            print()
            print(f"3. FOUND {len(markets)} MARKETS")

            print()
            filtered_markets = self.agent.filter_markets(markets)
            print(f"4. FILTERED {len(filtered_markets)} MARKETS")

            # TODO: Re-enable date filtering once market data format is confirmed
            # Currently all markets are being filtered out - need to debug date format
            print(f"4.5. DATE FILTER TEMPORARILY DISABLED FOR TESTING")

            if not filtered_markets:
                raise ValueError("No markets available after filtering")

            random.shuffle(filtered_markets)
            market = filtered_markets[0]
            
            # Get full analysis including superforecasting reasoning
            full_analysis = self.agent.source_best_trade(market)
            print(f"5. CALCULATED TRADE {full_analysis}")

            # Parse trade recommendation
            trade_data = self._parse_trade_recommendation(full_analysis, market)
            trade_data["full_analysis"] = full_analysis  # Save complete analysis
            
            amount = self.agent.format_trade_prompt_for_execution(full_analysis)
            
            # Print clean summary
            self._print_trade_summary(trade_data, execute, amount)
            
            # Save to file
            self._save_trade_recommendation(trade_data, execute)
            
            # Trading is disabled by default for TOS compliance.
            # Set execute=True (and ensure you comply with polymarket.com/tos)
            if execute:
                trade = self.polymarket.execute_market_order(market, amount)
                print(f"\n✅ TRADE EXECUTED: {trade}")
            else:
                print(f"\n⚠️  DRY RUN MODE - No trade was executed")
                print(f"💡 To execute this trade, run with: --execute true")

        except Exception as e:
            if retry_count < max_retries:
                print(f"Error {e} \n \n Retrying ({retry_count + 1}/{max_retries})...")
                self.one_best_trade(execute=execute, max_retries=max_retries, retry_count=retry_count + 1)
            else:
                print(f"Failed after {max_retries} attempts. Last error: {e}")
                raise

    def _parse_trade_recommendation(self, best_trade: str, market) -> dict:
        """Extract trade details from AI recommendation"""
        try:
            import ast
            # Extract price, size, side from the response
            price_match = re.search(r'price[:\s]*([0-9.]+)', best_trade)
            size_match = re.search(r'size[:\s]*([0-9.]+)', best_trade)
            side_match = re.search(r'side[:\s]*(BUY|SELL)', best_trade, re.IGNORECASE)
            
            market_doc = market[0].dict()
            market_meta = market_doc["metadata"]
            
            # Parse outcomes and prices properly
            outcomes = market_meta["outcomes"]
            if isinstance(outcomes, str):
                outcomes = ast.literal_eval(outcomes)
            
            prices = market_meta["outcome_prices"]
            if isinstance(prices, str):
                prices = ast.literal_eval(prices)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "market": {
                    "question": market_meta["question"],
                    "outcomes": outcomes,
                    "current_prices": prices,
                    "description": market_doc["page_content"][:200] + "...",
                    "end_date": market_meta.get("end", None)
                },
                "recommendation": {
                    "price": float(price_match.group(1)) if price_match else None,
                    "size": float(size_match.group(1)) if size_match else None,
                    "side": side_match.group(1).upper() if side_match else None,
                    "raw": best_trade
                }
            }
        except Exception as e:
            print(f"Warning: Could not parse trade details: {e}")
            return {"error": str(e), "raw": best_trade}

    def _print_trade_summary(self, trade_data: dict, execute: bool, amount: float):
        """Print a clean, readable summary of the trade recommendation"""
        print("\n" + "="*80)
        print("🤖 AUTONOMOUS TRADER RECOMMENDATION")
        print("="*80)
        
        if "error" in trade_data:
            print(f"\n⚠️  Could not parse recommendation")
            print(f"Raw output: {trade_data.get('raw', 'N/A')}")
            return
        
        market = trade_data.get("market", {})
        rec = trade_data.get("recommendation", {})
        
        print(f"\n📊 MARKET:")
        print(f"   Question: {market.get('question', 'N/A')}")
        print(f"   Outcomes: {market.get('outcomes', 'N/A')}")
        print(f"   Current Prices: {market.get('current_prices', 'N/A')}")
        
        print(f"\n💡 RECOMMENDATION:")
        print(f"   Side: {rec.get('side', 'N/A')}")
        print(f"   Target Price: {rec.get('price', 'N/A')}")
        print(f"   Position Size: {rec.get('size', 'N/A')*100 if rec.get('size') else 'N/A'}% of balance")
        print(f"   USDC Amount: ${amount:.2f}")
        
        print(f"\n⚙️  MODE: {'🔴 LIVE TRADING' if execute else '🟡 DRY RUN (No trades executed)'}")
        print("="*80 + "\n")

    def _save_trade_recommendation(self, trade_data: dict, executed: bool):
        """Save trade recommendation to JSON and readable text file"""
        try:
            trade_data["executed"] = executed
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save JSON version
            json_filename = f"trade_recommendation_{timestamp}.json"
            with open(json_filename, 'w') as f:
                json.dump(trade_data, f, indent=2)
            
            # Save human-readable version
            txt_filename = f"trade_recommendation_{timestamp}.txt"
            self._save_readable_recommendation(trade_data, txt_filename)
            
            print(f"📁 Recommendation saved to: {json_filename}")
            print(f"📄 Human-readable version: {txt_filename}")
        except Exception as e:
            print(f"Warning: Could not save recommendation to file: {e}")
    
    def _save_readable_recommendation(self, trade_data: dict, filename: str):
        """Save a clean, human-readable recommendation to a text file"""
        market = trade_data.get("market", {})
        rec = trade_data.get("recommendation", {})
        full_analysis = trade_data.get("full_analysis", "")
        
        outcomes = market.get('outcomes', ['Yes', 'No'])
        prices = market.get('current_prices', [])
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("POLYMARKET TRADE RECOMMENDATION\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n\n")
            
            f.write("MARKET DETAILS\n")
            f.write("-" * 80 + "\n")
            f.write(f"Question: {market.get('question', 'N/A')}\n")
            f.write(f"Outcomes: {', '.join(outcomes) if isinstance(outcomes, list) else str(outcomes)}\n")
            f.write(f"Current YES Price: ${prices[0] if prices and len(prices) > 0 else 'N/A'}\n")
            f.write(f"Current NO Price: ${prices[1] if prices and len(prices) > 1 else 'N/A'}\n\n")
            
            # Extract and format the superforecasting analysis
            if full_analysis:
                f.write("AI SUPERFORECASTING ANALYSIS\n")
                f.write("-" * 80 + "\n")
                
                # Split on "TRADE RECOMMENDATION:" to separate forecast from trade
                parts = full_analysis.split("TRADE RECOMMENDATION:")
                forecast_text = parts[0].strip()
                
                # Clean up the forecast text
                f.write(forecast_text)
                f.write("\n\n")
            
            f.write("TRADE RECOMMENDATION\n")
            f.write("-" * 80 + "\n")
            side = rec.get('side', 'N/A')
            price = rec.get('price', 'N/A')
            size_pct = rec.get('size', 0) * 100 if rec.get('size') else 'N/A'
            
            f.write(f"ACTION: {side}\n")
            f.write(f"Outcome to buy: {'YES' if side == 'BUY' else 'NO' if side == 'SELL' else 'N/A'}\n")
            f.write(f"Target Price: ${price}\n")
            f.write(f"Position Size: {size_pct}% of your balance\n\n")
            
            f.write("HOW TO EXECUTE ON POLYMARKET\n")
            f.write("-" * 80 + "\n")
            f.write("1. Go to: polymarket.com\n")
            f.write("2. Search for the market question above\n")
            f.write(f"3. Select the '{('YES' if side == 'BUY' else 'NO')}' outcome\n")
            f.write(f"4. Enter your desired amount (recommended: {size_pct}% of balance)\n")
            f.write(f"5. Set limit price to: ${price} (or use market price if close)\n")
            f.write("6. Review and confirm your trade\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("DISCLAIMER: This is AI-generated advice. Do your own research.\n")
            f.write("Trade at your own risk. Past performance doesn't guarantee future results.\n")
            f.write("=" * 80 + "\n")
    
    def _save_multiple_recommendations(self, recommendations: list, executed: bool):
        """Save multiple trade recommendations to a JSON file"""
        try:
            data = {
                "executed": executed,
                "timestamp": datetime.now().isoformat(),
                "count": len(recommendations),
                "recommendations": recommendations
            }
            filename = f"trade_recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"📁 {len(recommendations)} recommendations saved to: {filename}")
        except Exception as e:
            print(f"Warning: Could not save recommendations to file: {e}")

    def maintain_positions(self):
        pass

    def incentive_farm(self):
        pass


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    execute = False
    if "--execute" in sys.argv:
        idx = sys.argv.index("--execute")
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1].lower() == "true":
            execute = True
    
    t = Trader()
    t.one_best_trade(execute=execute)
