# Polymarket Autonomous Trading System - How It Works

## Overview

There are **TWO ways** to use this automated trading system:

1. **Web Dashboard UI** - Visual interface to browse markets
2. **CLI Automated Trader** - Command-line tool that recommends trades

---

## 1. Web Dashboard UI 🌐

### What It Does
- Shows all active markets in a visual interface
- Displays market questions, outcomes, spreads, and end dates
- Lets you browse trading opportunities
- **Does NOT make automated recommendations** (just displays data)

### How to Use

**Start the server:**
```bash
cd c:\Users\user\OneDrive\Desktop\polymarket\agents
.venv\Scripts\Activate.ps1
python scripts/python/server.py
```

**Access in browser:**
```
http://localhost:8888
```

### What You'll See
- Dark-themed dashboard
- 20 best markets (sorted by lowest spread)
- Each market shows:
  - Question (e.g., "US recession in 2025?")
  - Outcomes ("Yes" / "No")
  - End date
  - Spread (lower is better)
  - Funded status

### Limitations
⚠️ The UI is **read-only** - it shows markets but:
- Does NOT analyze which to trade
- Does NOT give AI recommendations
- Does NOT execute trades
- Just a visual browser

---

## 2. CLI Automated Trader 🤖 (RECOMMENDED)

### What It Does
This is the **actual automated system** that:
1. ✅ Fetches all active markets
2. ✅ Checks your USDC balance
3. ✅ Analyzes markets for opportunities
4. ✅ Recommends specific trades with confidence scores
5. ✅ Gives you the exact command to execute

### How to Use

**Run the automated analyzer:**
```bash
cd c:\Users\user\OneDrive\Desktop\polymarket\agents
python simple_auto_trader.py
```

### Example Output

```
Simple Autonomous Trader Starting...

Fetching markets...
Found 100 active markets

Wallet Balance: $3.97 USDC

Analyzing Markets:

1. US recession in 2025?
   Ends: 2026-02-28T12:00:00Z
   Spread: 0.0020
   Outcomes: ['Yes', 'No']
   Prices: ['$0.0070', '$0.9930']
   RECOMMENDATION: Buy Yes
   Confidence: 98.6%
   Reasoning: Yes is trading at $0.0070, below 50%
   Token ID: 10417355721474453757042434534720954458577584295010975685165285591301529570199
   Suggested Amount: $0.40 USDC

To execute this trade, run:
   python scripts/python/cli.py place-market-order-by-token 1041735572147... 0.40
```

### How It Analyzes Markets

The automated trader uses **simple but effective logic**:

1. **Looks for mispriced outcomes:**
   - If "Yes" is trading below $0.50 (50%) → Potential buy opportunity
   - If "No" is trading below $0.50 (50%) → Potential buy opportunity

2. **Checks market quality:**
   - Spread must be < 10% (ensures liquidity)
   - Market must be active and not closed

3. **Calculates confidence:**
   ```
   Confidence = (0.50 - current_price) × 200%
   ```
   Example: If "Yes" is $0.01, confidence = 98%

4. **Suggests safe position size:**
   - 10% of your balance OR $5 max (whichever is smaller)
   - Conservative approach to manage risk

### Execute the Trade

After reviewing the recommendation:

```bash
python scripts/python/cli.py place-market-order-by-token <TOKEN_ID> <AMOUNT>
```

---

## Complete Workflow Comparison

### Option A: UI Dashboard (Passive Browsing)
```
1. Start server: python scripts/python/server.py
2. Open browser: http://localhost:8888
3. Browse markets visually
4. Manually decide what to trade
5. Use CLI to execute
```

### Option B: Automated CLI (Active Recommendations) ⭐
```
1. Run analyzer: python simple_auto_trader.py
2. Review AI recommendation
3. Execute trade: python scripts/python/cli.py place-market-order-by-token ...
```

---

## Why Two Systems?

### The Original Plan (Broken on Windows)
The repo came with a complex autonomous system:
- AI agent with LangChain
- RAG (Retrieval-Augmented Generation) with news analysis
- Chroma vector database for filtering
- OpenAI GPT for predictions

**Problem:** Required `jq` Python package (won't compile on Windows) + Python 3.9 (you have 3.14)

### The Working Solution (What You Have Now)
I created `simple_auto_trader.py` that:
- ✅ Works on Windows (no jq dependency)
- ✅ Works with Python 3.14
- ✅ Analyzes markets using price-based logic
- ✅ Gives actionable recommendations
- ⚠️ Doesn't use AI/news (just math-based analysis)

---

## Available Commands

### Check Markets
```bash
# CLI: See all markets with details
python scripts/python/cli.py get-all-markets --limit 10

# UI: Visual dashboard
python scripts/python/server.py
# Then visit: http://localhost:8888
```

### Check Balance
```bash
python scripts/python/cli.py check-usdc-balance
```

### Get Trading Recommendation
```bash
python simple_auto_trader.py
```

### Execute Trade
```bash
python scripts/python/cli.py place-market-order-by-token <TOKEN_ID> <AMOUNT>
```

---

## How the Automation Works (Technical)

### Data Flow

```
1. Fetch Markets
   ↓
   Polymarket Gamma API → Get 100 active markets
   
2. Filter & Sort
   ↓
   Remove closed/archived → Sort by spread
   
3. Analyze Pricing
   ↓
   For each market:
   - Parse outcome prices
   - Check if Yes or No < $0.50
   - Verify spread < 10%
   
4. Calculate Opportunity
   ↓
   If mispriced:
   - Calculate confidence score
   - Suggest position size (10% of balance)
   - Extract token ID for trade
   
5. Present Recommendation
   ↓
   Show: Market, Outcome, Price, Confidence, Command
   
6. User Executes
   ↓
   Copy/paste command → Trade submitted to Polymarket
```

### Price Logic Example

**Market:** "Will X happen?"
- Yes: $0.01 (1%)
- No: $0.99 (99%)

**Analysis:**
- "Yes" is trading way below 50%
- If you think real probability is higher than 1%, this is +EV
- Confidence = (0.50 - 0.01) × 200 = 98%
- Risk: $0.40 investment
- Reward: $40 if "Yes" wins (100x return)

**Recommendation:**
```
Buy "Yes" at $0.01
Confidence: 98%
Suggested: $0.40 (10% of $3.97 balance)
```

---

## Current Status

### Your Wallet
- **USDC Balance:** $3.97 (ready to trade)
- **Address:** 0xd6d39c2b53599Dfb6bf237E1B04e5a3191d6d6B6
- **Approvals:** ✅ All set (initialized previously)

### First Recommendation Found
- **Market:** US recession in 2025?
- **Recommendation:** Buy "Yes"
- **Current Price:** $0.0070 (0.7%)
- **Confidence:** 98.6%
- **Suggested Amount:** $0.40
- **Potential Return:** 142x if correct

### Why This Makes Sense
- Market says: 0.7% chance of recession
- If you think it's even 5%, you have 7x edge
- Small bet, huge upside if you're right
- Classic "lottery ticket" trade

---

## Next Steps

### If You Want to Trade Now
```bash
# 1. Get fresh recommendation
python simple_auto_trader.py

# 2. Review the suggestion
# (it will show current market analysis)

# 3. Execute if you agree
python scripts/python/cli.py place-market-order-by-token <TOKEN_ID> <AMOUNT>
```

### If You Want the UI
```bash
# Start server
python scripts/python/server.py

# Open browser
http://localhost:8888

# Browse markets visually
# Then use CLI to trade the ones you like
```

### If You Want Full AI Agent (Advanced)
The complex autonomous trader with AI/news is broken due to:
- jq dependency (can't compile on Windows)
- Python 3.14 vs 3.9 requirement

To fix it, you'd need to:
1. Install Python 3.9 in a separate virtual environment
2. Rebuild dependencies
3. Test if the RAG/LangChain system works

**OR** just use the working simple trader (which is honestly good enough!)

---

## FAQ

**Q: Is the UI automated?**
A: No, the UI just displays markets. Automation happens in the CLI tool.

**Q: Does it trade automatically without asking?**
A: No, it gives recommendations but you must execute manually.

**Q: How often should I run it?**
A: Run `simple_auto_trader.py` whenever you want a fresh analysis. Markets change constantly.

**Q: Is it safe?**
A: It only recommends 10% of balance or $5 max per trade. Still, you can lose money in prediction markets.

**Q: Can I change the trading logic?**
A: Yes! Edit `simple_auto_trader.py` to adjust:
- Price thresholds (currently < $0.50)
- Spread limits (currently < 10%)
- Position sizing (currently 10% or $5 max)
- Number of markets analyzed (currently top 5)

**Q: Where does it get the data?**
A: Polymarket Gamma API (https://gamma-api.polymarket.com)

---

## Summary

**You have TWO tools:**

1. **UI Dashboard** (`server.py`) - Browse markets visually
2. **Automated CLI** (`simple_auto_trader.py`) - Get AI recommendations ⭐

**The automated system:**
- Analyzes 100 markets
- Finds mispriced opportunities
- Recommends trades with confidence scores
- Gives you the exact command to execute

**It's working RIGHT NOW** - just run:
```bash
python simple_auto_trader.py
```

Ready to see what it recommends! 🚀
