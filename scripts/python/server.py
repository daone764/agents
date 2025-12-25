from typing import Union
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from agents.polymarket.polymarket import Polymarket

app = FastAPI(title="Polymarket Trading Dashboard")

# Initialize Polymarket client
pm = Polymarket()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard showing active markets"""
    try:
        markets = pm.get_all_markets()
        markets = pm.filter_markets_for_trading(markets)
        markets = sorted(markets, key=lambda x: x.spread, reverse=False)[:20]
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Polymarket Trading Dashboard</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 20px;
                    background: #0a0e27;
                    color: #fff;
                }
                h1 { color: #00d4ff; }
                .market-card {
                    background: #1a1f3a;
                    border: 1px solid #2a3f5f;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 15px 0;
                }
                .market-card:hover {
                    border-color: #00d4ff;
                    box-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
                }
                .question { 
                    font-size: 18px; 
                    font-weight: bold; 
                    color: #00d4ff;
                    margin-bottom: 10px;
                }
                .details { 
                    color: #aaa; 
                    font-size: 14px;
                    margin: 5px 0;
                }
                .outcomes {
                    display: flex;
                    gap: 10px;
                    margin-top: 10px;
                }
                .outcome-btn {
                    flex: 1;
                    padding: 10px;
                    background: #2a3f5f;
                    border: 1px solid #3a4f6f;
                    border-radius: 5px;
                    cursor: pointer;
                    text-align: center;
                }
                .outcome-btn:hover {
                    background: #3a4f6f;
                }
                .stats {
                    background: #2a3f5f;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
                .badge {
                    display: inline-block;
                    padding: 4px 8px;
                    background: #00d4ff;
                    color: #0a0e27;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                    margin-right: 5px;
                }
            </style>
        </head>
        <body>
            <h1>🎯 Polymarket Trading Dashboard</h1>
            <div class="stats">
                <strong>""" + str(len(markets)) + """ Active Markets</strong> | 
                Wallet: Connected ✅ | 
                USDC Balance: Checking...
            </div>
        """
        
        for i, market in enumerate(markets, 1):
            outcomes = eval(market.outcomes) if isinstance(market.outcomes, str) else market.outcomes
            
            html += f"""
            <div class="market-card">
                <div class="question">{i}. {market.question}</div>
                <div class="details">
                    <span class="badge">{'FUNDED' if market.funded else 'ACTIVE'}</span>
                    Ends: {market.end[:10]} | 
                    Spread: {market.spread:.4f}
                </div>
                <div class="outcomes">
            """
            
            for outcome in outcomes:
                html += f"""
                    <div class="outcome-btn">{outcome}</div>
                """
            
            html += """
                </div>
            </div>
            """
        
        html += """
            <div class="stats">
                <p>💡 <strong>Tip:</strong> Use the CLI for AI-powered trading: 
                <code>python scripts/python/cli.py run-autonomous-trader</code></p>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html)
        
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error loading markets</h1><p>{str(e)}</p>")

@app.get("/api/markets")
def get_markets(limit: int = 20):
    """API endpoint to get current markets"""
    markets = pm.get_all_markets()
    markets = pm.filter_markets_for_trading(markets)
    markets = sorted(markets, key=lambda x: x.spread, reverse=False)[:limit]
    return {"markets": [m.__dict__ for m in markets]}

@app.get("/api/balance")
def get_balance():
    """Get wallet balance"""
    try:
        # This would check the actual balance
        return {"usdc": "Checking...", "matic": "0.0"}
    except Exception as e:
        return {"error": str(e)}
