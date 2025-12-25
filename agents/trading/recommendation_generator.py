"""
Recommendation Generator
Produces clean, structured trade recommendations with table formatting.
Supports near-miss output and manual check suggestions for EOY mode.
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

from agents.trading.api_client import Market
from agents.trading.edge_model import EdgeAnalysis, TradeAction
from agents.trading.position_sizing import PositionRecommendation

logger = logging.getLogger(__name__)

# Import bracket strategy types (optional - graceful fallback if not available)
try:
    from agents.trading.bracket_strategy import BracketStrategy, BracketStrategyGenerator
    BRACKET_SUPPORT = True
except ImportError:
    BRACKET_SUPPORT = False
    BracketStrategy = None


class RecommendationGenerator:
    """
    Generates clean, structured trade recommendations.
    Includes market links and near-miss suggestions.
    """
    
    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate(
        self,
        analysis: EdgeAnalysis,
        position: PositionRecommendation,
        bankroll: float
    ) -> str:
        """
        Generate a complete trade recommendation.
        
        Returns:
            Formatted recommendation string
        """
        market = analysis.market
        action = analysis.recommended_action
        
        # Determine which outcome to trade
        if action == TradeAction.BUY_YES:
            outcome = "YES"
            entry_price = market.yes_price
            model_prob = analysis.model_yes_prob
        elif action == TradeAction.BUY_NO:
            outcome = "NO"
            entry_price = market.no_price
            model_prob = analysis.model_no_prob
        else:
            outcome = "N/A"
            entry_price = 0
            model_prob = 0
        
        # Format resolution date
        if market.end_date:
            resolution_date = market.end_date.strftime("%B %d, %Y")
            days_left = market.days_to_resolution
        else:
            resolution_date = "Unknown"
            days_left = "Unknown"
        
        recommendation = f"""================================================================================
POLYMARKET TRADE RECOMMENDATION
================================================================================

Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC

MARKET DETAILS
--------------------------------------------------------------------------------
Question: {market.question}
Market Link: {market.market_url}
Outcomes: Yes / No
Current YES Price: ${market.yes_price:.4f}
Current NO Price: ${market.no_price:.4f}
Volume (24h): ${market.volume_24h:,.0f}
Total Volume: ${market.volume:,.0f}
Resolution Date: {resolution_date} ({days_left} days)

MODEL FORECAST
--------------------------------------------------------------------------------
Estimated probability of YES: {analysis.model_yes_prob * 100:.1f}%
Estimated probability of NO: {analysis.model_no_prob * 100:.1f}%
Confidence: {analysis.confidence.upper()}

EDGE ANALYSIS
--------------------------------------------------------------------------------
YES edge: {analysis.yes_edge:+.1f}%
NO edge: {analysis.no_edge:+.1f}%
Detected edge: {analysis.edge_percent:.1f}% on {outcome}
Potential ROI: {analysis.potential_roi:.1f}%
Required threshold: {"8.0% (short-term)" if days_left and days_left < 14 else "5.0%"} ({"MET ✓" if analysis.meets_threshold else "NOT MET ✗"})

TRADE RECOMMENDATION
--------------------------------------------------------------------------------
ACTION: {"BUY " + outcome if position.should_trade else "NO TRADE"}
Target Entry Price: ${entry_price:.4f} (market order) / ${analysis.target_price:.4f} (limit order)
Position Size: {position.position_percent:.1f}% of bankroll (≈ ${position.position_usd:.2f})
Risk Level: {position.risk_level}
"""
        # Add sports warning if applicable
        if analysis.is_sports:
            recommendation += """
⚠️ SPORTS MARKET WARNING
--------------------------------------------------------------------------------
This is a sports market. Sports predictions are notoriously difficult and 
our model may be miscalibrated. Consider:
- Reducing position size by 50%
- Setting a tighter stop loss
- Verifying with external sports analysis
--------------------------------------------------------------------------------
"""
        
        # Add cap warning if model was adjusted
        if analysis.was_capped:
            recommendation += f"""
ℹ️ MODEL ADJUSTMENT APPLIED
--------------------------------------------------------------------------------
{analysis.cap_reason}
Original model output was adjusted to prevent overconfident predictions.
--------------------------------------------------------------------------------
"""

        recommendation += f"""
HOW TO EXECUTE ON POLYMARKET.COM
--------------------------------------------------------------------------------
1. Visit: {market.market_url}
2. Click on the {outcome} outcome
3. For market order: Buy at ${entry_price:.4f}
4. For limit order: Set limit price at ${analysis.target_price:.4f} (2% discount)
5. Enter amount: ${position.position_usd:.2f}
6. Review and confirm

================================================================================
⚠️ This is automated analysis. Always verify and use your judgment.
Past performance does not guarantee future results. Trade at your own risk.
================================================================================
"""
        return recommendation
    
    def generate_no_trade(self, reason: str, near_misses: List[Dict] = None) -> str:
        """Generate a no-trade recommendation with reason and near-miss suggestions"""
        output = f"""================================================================================
POLYMARKET ANALYSIS - NO TRADE RECOMMENDED
================================================================================

Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC

RECOMMENDATION: NO TRADE

Reason: {reason}

"""
        # Add near-miss suggestions if available
        if near_misses and len(near_misses) > 0:
            output += """
NO STRONG RECOMMENDATIONS, BUT CHECK THESE MANUALLY:
--------------------------------------------------------------------------------
These markets almost passed our filters and may be worth a look:

"""
            for i, nm in enumerate(near_misses[:5], 1):
                category = nm.get('category', 'Other') or 'Other'
                output += f"""{i}. {nm.get('question', 'Unknown')}
   Volume: ${nm.get('volume', 0):,.0f} | 24h: ${nm.get('volume_24h', 0):,.0f}
   Days to resolution: {nm.get('days_to_resolution', '?')}
   Prices: Yes ${nm.get('prices', [0,0])[0]:.2f} / No ${nm.get('prices', [0,0])[1] if len(nm.get('prices', [])) > 1 else 0:.2f}
   Category: {category}
   Why filtered: {nm.get('reason', 'Unknown')}
   Near-miss score: {nm.get('score', 0):.0f}/100

"""
        
        output += """================================================================================
"""
        return output
    
    def save_recommendation(
        self,
        recommendation: str,
        prefix: str = "trade_rec"
    ) -> str:
        """Save recommendation to file and return filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"{prefix}_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(recommendation)
        
        logger.info(f"Recommendation saved to: {filename}")
        return str(filename)
    
    def save_html(self, html_content: str, prefix: str = "report") -> str:
        """Save HTML report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"{prefix}_{timestamp}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML report saved to: {filename}")
        return str(filename)
    
    def _get_html_styles(self) -> str:
        """Return CSS styles for HTML reports - clean professional design"""
        return """
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            
            body {
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
                background: #f5f5f5;
                color: #333;
                line-height: 1.6;
                padding: 20px;
            }
            
            .container {
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                padding: 30px;
            }
            
            .header {
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #eee;
            }
            
            .header h1 {
                font-size: 24px;
                color: #333;
                margin-bottom: 5px;
            }
            
            .header .subtitle {
                color: #666;
                font-size: 14px;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                margin-bottom: 30px;
            }
            
            .stat-card {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 15px;
                text-align: center;
            }
            
            .stat-card .value {
                font-size: 28px;
                font-weight: 700;
                color: #2563eb;
            }
            
            .stat-card .label {
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }
            
            .section {
                margin-bottom: 25px;
            }
            
            .section-title {
                font-size: 16px;
                font-weight: 600;
                color: #333;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 1px solid #eee;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
            }
            
            th, td {
                padding: 10px 12px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            
            th {
                background: #f8f9fa;
                font-weight: 600;
                color: #555;
                font-size: 12px;
                text-transform: uppercase;
            }
            
            tr:hover {
                background: #f8f9fa;
            }
            
            .trade-row {
                background: #e8f5e9 !important;
            }
            
            .trade-row:hover {
                background: #c8e6c9 !important;
            }
            
            .badge {
                display: inline-block;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }
            
            .badge-success {
                background: #d4edda;
                color: #155724;
            }
            
            .badge-neutral {
                background: #e9ecef;
                color: #6c757d;
            }
            
            .trade-link {
                display: inline-block;
                padding: 5px 12px;
                background: #2563eb;
                color: white !important;
                text-decoration: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
            }
            
            .trade-link:hover {
                background: #1d4ed8;
            }
            
            .link-secondary {
                color: #2563eb;
                text-decoration: none;
                font-size: 12px;
            }
            
            .link-secondary:hover {
                text-decoration: underline;
            }
            
            .edge-positive { color: #16a34a; font-weight: 600; }
            .edge-negative { color: #dc2626; }
            
            .recommended-section {
                background: #e8f5e9;
                border: 1px solid #a5d6a7;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 25px;
            }
            
            .recommended-section .section-title {
                color: #2e7d32;
                border-bottom-color: #a5d6a7;
            }
            
            .trade-card {
                background: white;
                border-radius: 6px;
                padding: 15px;
                margin-bottom: 15px;
                border: 1px solid #c8e6c9;
            }
            
            .trade-card h3 {
                font-size: 14px;
                margin-bottom: 10px;
                color: #333;
            }
            
            .trade-details {
                display: flex;
                gap: 20px;
                margin-bottom: 15px;
                flex-wrap: wrap;
            }
            
            .trade-detail {
                text-align: center;
            }
            
            .trade-detail .label {
                font-size: 11px;
                color: #666;
                text-transform: uppercase;
            }
            
            .trade-detail .value {
                font-size: 16px;
                font-weight: 600;
            }
            
            .big-trade-btn {
                display: inline-block;
                padding: 10px 20px;
                background: #2563eb;
                color: white !important;
                text-decoration: none;
                border-radius: 5px;
                font-weight: 600;
                font-size: 14px;
            }
            
            .big-trade-btn:hover {
                background: #1d4ed8;
            }
            
            .near-miss-card {
                background: #fff8e1;
                border-left: 3px solid #ffc107;
                padding: 10px 15px;
                margin-bottom: 10px;
            }
            
            .near-miss-card strong {
                font-size: 13px;
            }
            
            .footer {
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 12px;
                border-top: 1px solid #eee;
                margin-top: 20px;
            }
        </style>
        """
    
    def generate_html_summary(
        self,
        markets_scanned: int,
        markets_valid: int,
        trades_recommended: int,
        rejections_by_reason: dict,
        near_misses: List[Dict] = None,
        analyzed_markets: List[Dict] = None,
        bracket_strategies: List = None
    ) -> str:
        """Generate beautiful HTML daily summary report"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Calculate hit rate
        hit_rate = (trades_recommended / markets_valid * 100) if markets_valid > 0 else 0
        
        # Build rejection breakdown HTML
        rejections_html = ""
        for reason, count in sorted(rejections_by_reason.items(), key=lambda x: -x[1]):
            rejections_html += f'<tr><td>{reason}</td><td style="text-align:right">{count}</td></tr>'
        
        # Build analyzed markets table
        markets_html = ""
        if analyzed_markets:
            for am in analyzed_markets[:15]:
                action = am.get('action', 'NO_TRADE')
                question = am.get('question', 'Unknown')
                model_pct = am.get('model_prob', 0) * 100
                market_pct = am.get('market_price', 0) * 100
                edge = am.get('edge', 0)
                url = am.get('url', '#')
                
                is_trade = action in ('BUY_YES', 'BUY_NO')
                row_class = 'trade-row' if is_trade else ''
                
                # Edge coloring
                edge_class = 'edge-positive' if edge > 0 else 'edge-negative' if edge < 0 else ''
                
                # Action badge
                if action == 'BUY_YES':
                    badge = '<span class="badge badge-success">BUY YES</span>'
                elif action == 'BUY_NO':
                    badge = '<span class="badge badge-success">BUY NO</span>'
                else:
                    badge = '<span class="badge badge-neutral">NO TRADE</span>'
                
                # Link for trades
                link_html = f'<a href="{url}" target="_blank" class="trade-link">Trade Now →</a>' if is_trade else f'<a href="{url}" target="_blank" class="link-secondary">View</a>'
                
                markets_html += f'''
                <tr class="{row_class}">
                    <td><strong>{question[:60]}{"..." if len(question) > 60 else ""}</strong></td>
                    <td style="text-align:center">{model_pct:.0f}%</td>
                    <td style="text-align:center">{market_pct:.0f}%</td>
                    <td style="text-align:center" class="{edge_class}">{edge:+.1f}%</td>
                    <td style="text-align:center">{badge}</td>
                    <td style="text-align:center">{link_html}</td>
                </tr>'''
        
        # Build recommended trades section
        recommended = [am for am in (analyzed_markets or []) if am.get('action') in ('BUY_YES', 'BUY_NO')]
        recommended_html = ""
        if recommended:
            for i, am in enumerate(recommended, 1):
                url = am.get('url', '#')
                edge = am.get('edge', 0)
                model_pct = am.get('model_prob', 0) * 100
                market_pct = am.get('market_price', 0) * 100
                action = am.get('action', 'BUY_YES')
                
                recommended_html += f'''
                <div class="trade-card">
                    <h3>#{i} {am.get('question', 'Unknown')}</h3>
                    <div class="trade-details">
                        <div class="trade-detail">
                            <div class="label">Action</div>
                            <div class="value" style="color: #34d399">{action.replace('_', ' ')}</div>
                        </div>
                        <div class="trade-detail">
                            <div class="label">Edge</div>
                            <div class="value edge-positive">{edge:+.1f}%</div>
                        </div>
                        <div class="trade-detail">
                            <div class="label">Model</div>
                            <div class="value">{model_pct:.0f}%</div>
                        </div>
                        <div class="trade-detail">
                            <div class="label">Market</div>
                            <div class="value">{market_pct:.0f}%</div>
                        </div>
                    </div>
                    <a href="{url}" target="_blank" class="big-trade-btn">Trade on Polymarket →</a>
                </div>'''
        
        # Build near-misses section
        near_misses_html = ""
        if near_misses:
            for nm in near_misses[:5]:
                question = nm.get('question', 'Unknown')
                vol = nm.get('volume', 0)
                reason = nm.get('reason', 'Unknown')
                # Use actual URL from API, fallback to polymarket search
                url = nm.get('url', '') or f"https://polymarket.com/markets?_q={question[:30].replace(' ', '+')}"
                
                near_misses_html += f'''
                <div class="near-miss-card">
                    <strong>{question}</strong>
                    <div style="font-size: 12px; color: #666; margin-top: 5px">
                        Volume: ${vol:,.0f} | {reason}
                    </div>
                    <div style="margin-top: 8px">
                        <a href="{url}" target="_blank" class="link-secondary">View on Polymarket →</a>
                    </div>
                </div>'''
        
        # Build recommended trades section HTML
        recommended_section_html = ""
        if recommended:
            recommended_section_html = f'''
        <div class="recommended-section">
            <div class="section-title"><span class="icon">🎯</span> Recommended Trades</div>
            {recommended_html}
        </div>
        '''
        
        # Build near-misses section HTML
        near_misses_section_html = ""
        if near_misses:
            near_misses_section_html = f'''
        <div class="section">
            <div class="section-title"><span class="icon">👀</span> Near-Miss Markets (Review Manually)</div>
            <p style="color: var(--gray); margin-bottom: 1rem">These high-volume markets almost passed filters:</p>
            {near_misses_html}
        </div>
        '''
        
        # Build bracket strategies HTML
        bracket_section_html = ""
        if bracket_strategies and BRACKET_SUPPORT:
            generator = BracketStrategyGenerator()
            bracket_css = generator.get_bracket_css()
            for strategy in bracket_strategies:
                bracket_section_html += generator.format_strategy_html(strategy)
        else:
            bracket_css = ""
        
        # Assemble full HTML
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polymarket Trading Report - {datetime.now().strftime("%Y-%m-%d")}</title>
    {self._get_html_styles()}
    <style>{bracket_css}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Polymarket Trading Report</h1>
            <div class="subtitle">Generated: {timestamp}</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="value">{markets_scanned}</div>
                <div class="label">Markets Scanned</div>
            </div>
            <div class="stat-card">
                <div class="value">{markets_valid}</div>
                <div class="label">Passed Filters</div>
            </div>
            <div class="stat-card">
                <div class="value">{trades_recommended}</div>
                <div class="label">Trades Recommended</div>
            </div>
            <div class="stat-card">
                <div class="value">{hit_rate:.1f}%</div>
                <div class="label">Hit Rate</div>
            </div>
        </div>
        
        {bracket_section_html}
        
        {recommended_section_html}
        
        <div class="section">
            <div class="section-title"><span class="icon">📈</span> All Analyzed Markets</div>
            <table>
                <thead>
                    <tr>
                        <th>Market</th>
                        <th style="text-align:center">Model</th>
                        <th style="text-align:center">Market Price</th>
                        <th style="text-align:center">Edge</th>
                        <th style="text-align:center">Action</th>
                        <th style="text-align:center">Link</th>
                    </tr>
                </thead>
                <tbody>
                    {markets_html}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <div class="section-title"><span class="icon">📋</span> Rejection Breakdown</div>
            <table>
                <thead>
                    <tr><th>Reason</th><th style="text-align:right">Count</th></tr>
                </thead>
                <tbody>
                    {rejections_html}
                </tbody>
            </table>
        </div>
        
        {near_misses_section_html}
        
        <div class="footer">
            <p>⚠️ This is automated analysis. Always verify and use your judgment.</p>
            <p>Past performance does not guarantee future results. Trade at your own risk.</p>
            <p style="margin-top: 1rem">
                <a href="https://polymarket.com" target="_blank">Open Polymarket</a>
            </p>
        </div>
    </div>
</body>
</html>'''
        
        return html
    
    def generate_daily_summary(
        self,
        markets_scanned: int,
        markets_valid: int,
        trades_recommended: int,
        rejections_by_reason: dict,
        near_misses: List[Dict] = None,
        analyzed_markets: List[Dict] = None,
        bracket_strategies: List = None
    ) -> str:
        """Generate daily summary report with tables and highlighted recommendations"""
        summary = f"""
{'='*100}
                              POLYMARKET DAILY TRADING SUMMARY
{'='*100}

Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC

+-------------------------+----------------+
| SCAN RESULTS            |                |
+-------------------------+----------------+
| Markets scanned         | {markets_scanned:>14} |
| Markets passing filters | {markets_valid:>14} |
| Trades recommended      | {trades_recommended:>14} |
| Hit rate                | {(trades_recommended / markets_valid * 100) if markets_valid > 0 else 0:>13.1f}% |
+-------------------------+----------------+

REJECTION BREAKDOWN
"""
        for reason, count in sorted(rejections_by_reason.items(), key=lambda x: -x[1]):
            summary += f"  - {reason}: {count}\n"
        
        # Add bracket strategies (combined strategies for related markets)
        if bracket_strategies and BRACKET_SUPPORT:
            generator = BracketStrategyGenerator()
            for strategy in bracket_strategies:
                summary += generator.format_strategy_text(strategy)
        
        # Add analyzed markets with table format and highlights
        if analyzed_markets and len(analyzed_markets) > 0:
            summary += f"""
{'='*100}
                              MARKETS ANALYZED
{'='*100}

+{'='*50}+{'='*8}+{'='*8}+{'='*8}+{'='*15}+
| {'MARKET':<48} | {'MODEL':>6} | {'PRICE':>6} | {'EDGE':>6} | {'ACTION':<13} |
+{'-'*50}+{'-'*8}+{'-'*8}+{'-'*8}+{'-'*15}+
"""
            for am in analyzed_markets[:15]:
                action = am.get('action', 'NO_TRADE')
                question = am.get('question', 'Unknown')[:47]
                model_pct = am.get('model_prob', 0) * 100
                market_pct = am.get('market_price', 0) * 100
                edge = am.get('edge', 0)
                url = am.get('url', '')
                
                # Highlight YES recommendations
                if action in ('BUY_YES', 'BUY_NO'):
                    marker = ">>>"
                    action_str = f"*** {action} ***"
                else:
                    marker = "   "
                    action_str = action
                
                summary += f"|{marker}{question:<47} | {model_pct:>5.0f}% | {market_pct:>5.0f}% | {edge:>+5.1f}% | {action_str:<13} |\n"
            
            summary += f"+{'-'*50}+{'-'*8}+{'-'*8}+{'-'*8}+{'-'*15}+\n"
            
            # Add direct links for recommended trades
            recommended = [am for am in analyzed_markets if am.get('action') in ('BUY_YES', 'BUY_NO')]
            if recommended:
                summary += f"""
{'*'*100}
                         >>> RECOMMENDED TRADES - CLICK TO EXECUTE <<<
{'*'*100}
"""
                for i, am in enumerate(recommended, 1):
                    url = am.get('url', '')
                    summary += f"""
  [{i}] {am.get('question', 'Unknown')}
      ACTION: {am.get('action')} | Edge: {am.get('edge', 0):+.1f}% | Model: {am.get('model_prob', 0)*100:.0f}% vs Market: {am.get('market_price', 0)*100:.0f}%
      >>> TRADE HERE: {url}
"""
                summary += f"{'*'*100}\n"
        
        # Add near-miss suggestions with URLs
        if near_misses and len(near_misses) > 0:
            summary += f"""
{'='*100}
                     NEAR-MISS MARKETS (Review Manually)
{'='*100}
These high-volume markets almost passed filters - worth checking:

+{'-'*70}+{'-'*15}+{'-'*12}+
| {'MARKET':<68} | {'VOLUME':>13} | {'REASON':<10} |
+{'-'*70}+{'-'*15}+{'-'*12}+
"""
            for nm in near_misses[:8]:
                question = nm.get('question', 'Unknown')[:67]
                vol = nm.get('volume', 0)
                reason = nm.get('reason', 'Unknown')[:30].split(':')[0]
                summary += f"| {question:<68} | ${vol:>12,.0f} | {reason:<10} |\n"
            
            summary += f"+{'-'*70}+{'-'*15}+{'-'*12}+\n"
            
            summary += "\nMANUAL CHECK LINKS:\n"
            for i, nm in enumerate(near_misses[:5], 1):
                question = nm.get('question', 'Unknown')
                # Use actual URL from API, fallback to search
                url = nm.get('url', '') or f"https://polymarket.com/markets?_q={question[:30].replace(' ', '+')}"
                summary += f"  {i}. {question[:60]}\n     {url}\n"
        
        summary += f"""
{'='*100}
TIP: Run with --eoy flag for more relaxed filters on end-of-year markets.
For support: Review the generated trade_rec_*.txt files for full details.
{'='*100}
"""
        return summary
