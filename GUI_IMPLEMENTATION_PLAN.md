# Polymarket Autonomous Trader GUI - Implementation Plan
## **LOCAL WEB SERVER DEPLOYMENT**

## Project Overview
Build a local web-based GUI to visualize AI trading recommendations and execute trades on Polymarket. Runs on `localhost` - accessible only from your machine.

---

## Phase 1: Technology Stack (Simplified for Local)

### **Recommended Stack: FastAPI + React**
**Why:**
- ✅ FastAPI: Fast, modern Python API framework
- ✅ React: Rich UI components, real-time updates
- ✅ Both run on localhost (FastAPI: 8000, React: 3000)
- ✅ Clear separation of concerns
- ✅ Easy to extend

### **Alternative: Streamlit (Faster MVP)**
**Why:**
- ✅ 10x faster to build (all Python, no JavaScript)
- ✅ Auto-refresh, built-in components
- ✅ Single command to run: `streamlit run app.py`
- ✅ Perfect for local use
- ❌ Less customizable UI

### **Decision: Start with Streamlit, can add React later**
- Build Streamlit MVP in 1-2 days
- See if it meets your needs
- Upgrade to React if you need more control

---

## Phase 2: Local Architecture (Simplified)

```
┌──────────────────────────────────────────────────┐
│  Browser (Chrome/Firefox)                        │
│  http://localhost:8501                           │
└────────────────┬─────────────────────────────────┘
                 │
                 ↓
┌──────────────────────────────────────────────────┐
│  Streamlit Server (Port 8501)                    │
│  - Dashboard UI                                  │
│  - Real-time updates                             │
│  - Trade execution buttons                       │
└────────────────┬─────────────────────────────────┘
                 │
                 ↓
┌──────────────────────────────────────────────────┐
│  Python Backend (Your existing agents/)          │
│  - Trader class                                  │
│  - Polymarket API                                │
│  - OpenAI API                                    │
│  - Web3 / Polygon                                │
└──────────────────────────────────────────────────┘
```

**Super Simple:**
1. Run one command: `streamlit run gui/app.py`
2. Opens browser automatically to localhost:8501
3. Everything runs on your machine
4. No cloud, no deployment, no security concerns
```
┌─────────────────────────────────────────────────────────┐
│  🤖 Polymarket Autonomous Trader                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─── Wallet Status ─────────┐  ┌─── AI Status ──────┐ │
│  │ Connected: 0x1234...5678  │  │ Model: GPT-3.5     │ │
│  │ USDC: $1,234.56           │  │ Status: ✅ Active   │ │
│  │ MATIC: 2.5                │  │ Last Run: 2m ago   │ │
│  └───────────────────────────┘  └────────────────────┘ │
│                                                         │
│  ┌─── Current Recommendation ──────────────────────┐   │
│  │ 📊 Market: Will Alphabet be #1 by Dec 31?      │   │
│  │                                                 │   │
│  │ Current Price:  0.25% Yes  |  99.75% No        │   │
│  │ AI Prediction:  60% Yes                        │   │
│  │                                                 │   │
│  │ 💡 Recommendation: BUY YES @ 0.60              │   │
│  │    Position Size: 20% ($246.91)                │   │
│  │    Expected Value: +$147.45 (59.7% ROI)        │   │
│  │                                                 │   │
│  │  [🔄 Refresh]  [✅ Execute Trade]  [❌ Skip]    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

#### 2.2 Market Analysis View
- **Market Details Panel**
  - Full question & description
  - Resolution criteria
  - End date & time remaining
  - Volume & liquidity metrics
  
- **AI Reasoning Panel**
  - Superforecaster analysis breakdown
  - Key factors considered
  - Confidence score
  - Similar historical markets

- **Price Chart**
  - Current market prices (Yes/No)
  - Historical price movement
  - AI prediction vs market price gap

#### 2.3 Trade History View
```
┌─── Trade History ────────────────────────────────┐
│ Date       | Market           | Side | Size | P&L│
├────────────┼──────────────────┼──────┼──────┼────┤
│ 12/24 7:23 | Alphabet #1      | BUY  | $247 | -  │
│ 12/24 6:15 | Putin out by 2025| SELL | $150 | +$23│
│ 12/23 4:32 | Fed rate cut     | BUY  | $200 | +$45│
└──────────────────────────────────────────────────┘
```

#### 2.4 Settings & Configuration
- **Wallet Management**
  - Import private key (encrypted storage)
  - View wallet address
  - Check balances
  
- **Trading Parameters**
  - Max position size (% of balance)
  - Risk tolerance (conservative/moderate/aggressive)
  - Auto-execute trades (on/off)
  - Minimum confidence threshold
  
- **AI Configuration**
  - OpenAI API key
  - Model selection (GPT-3.5/GPT-4)
  - Refresh interval
  - Number of markets to analyze

---

## Phase 3: Quick Start Implementation (2-3 Hours)

### Step 1: Install Streamlit (5 minutes)
```bash
cd agents
pip install streamlit plotly pandas
```

### Step 2: Create GUI Directory (1 minute)
```bash
mkdir gui
cd gui
```

### Step 3: Create Basic Dashboard (2 hours)
Create `gui/app.py` - minimal working version:

```python
import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.application.trade import Trader
from agents.polymarket.polymarket import Polymarket
import json

st.set_page_config(page_title="Polymarket AI Trader", layout="wide", page_icon="🤖")

# Initialize
if 'trader' not in st.session_state:
    st.session_state.trader = Trader()
    st.session_state.polymarket = Polymarket()

# Header
st.title("🤖 Polymarket Autonomous Trader")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Wallet")
    address = st.session_state.polymarket.get_active_address()
    st.code(address, language=None)
    
    try:
        usdc = st.session_state.polymarket.get_usdc_balance()
        st.metric("USDC Balance", f"${usdc:.2f}")
    except:
        st.warning("⚠️ Could not fetch balance")
    
    st.markdown("---")
    st.header("🎯 Controls")
    auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📊 Latest Recommendation")
    
    if st.button("🔄 Get New Recommendation", type="primary"):
        with st.spinner("🤖 AI analyzing markets..."):
            # This will be replaced with actual recommendation loading
            st.info("Getting new recommendation...")

# Load latest recommendation file
import glob
files = glob.glob("trade_recommendation_*.json")
if files:
    latest = max(files)
    with open(latest, 'r') as f:
        rec = json.load(f)
    
    with col1:
        st.subheader("Market")
        st.info(rec['market']['question'])
        
        mc1, mc2 = st.columns(2)
        mc1.metric("Current Price", rec['market']['current_prices'])
        mc2.metric("Outcomes", rec['market']['outcomes'])
        
        st.subheader("💡 AI Recommendation")
        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("Side", rec['recommendation']['side'])
        rc2.metric("Target Price", rec['recommendation']['price'])
        rc3.metric("Position Size", f"{rec['recommendation']['size']*100}%")
        
        st.markdown("---")
        b1, b2, b3 = st.columns(3)
        
        if b1.button("✅ Execute Trade", use_container_width=True):
            st.success("Trade execution coming soon!")
        
        if b2.button("❌ Skip", use_container_width=True):
            st.info("Skipped")
        
        if b3.button("📊 More Details", use_container_width=True):
            with st.expander("Full Market Details", expanded=True):
                st.json(rec['market'])

with col2:
    st.header("📈 Stats")
    st.metric("Status", "✅ Active")
    st.metric("Recommendations", "1")
    st.metric("Win Rate", "N/A")

# Auto-refresh
if auto_refresh:
    import time
    time.sleep(30)
    st.rerun()
```

### Step 4: Run It! (1 minute)
```bash
streamlit run gui/app.py
```

**That's it!** Your browser opens to `http://localhost:8501` with the GUI running.
```
polymarket-trader-gui/
├── backend/
│   ├── agents/                    # Existing codebase
│   ├── api/
│   │   ├── __init__.py
│   │   ├── trader_service.py      # Wrapper for Trader class
│   │   ├── wallet_service.py      # Wallet operations
│   │   └── market_service.py      # Market data fetching
│   └── server.py                  # Flask/FastAPI server
│
├── frontend/
│   ├── streamlit_app.py           # Main Streamlit app (MVP)
│   ├── components/
│   │   ├── dashboard.py
│   │   ├── market_view.py
│   │   ├── trade_history.py
│   │   └── settings.py
│   └── utils/
│       ├── formatters.py
│       └── charts.py
│
├── data/
│   ├── trades.db                  # SQLite for trade history
│   └── config.json                # User preferences
│
└── requirements-gui.txt
```

### 3.2 Data Flow Architecture
```
┌─────────────┐
│   Frontend  │ (Streamlit/React)
│   (GUI)     │
└──────┬──────┘
       │ HTTP/WebSocket
       ↓
┌─────────────┐
│  API Layer  │ (FastAPI/Flask)
│  (Server)   │
└──────┬──────┘
       │
       ├─→ Trader Service → Autonomous Trader → OpenAI
       │
       ├─→ Wallet Service → Web3 → Polygon Network
       │
       └─→ Market Service → Polymarket API
```

### 3.3 Key Components to Build

#### Component 1: Backend API Server
```python
# backend/server.py
from fastapi import FastAPI, WebSocket
from agents.application.trade import Trader

app = FastAPI()
trader = Trader()

@app.get("/api/recommendation")
async def get_recommendation():
    """Get latest AI trade recommendation"""
    # Run trader.one_best_trade() in background
    # Return formatted recommendation
    pass

@app.post("/api/execute-trade")
async def execute_trade(trade_id: str, confirm: bool):
    """Execute a pending trade"""
    # Verify user confirmation
    # Execute trade via Polymarket
    # Return transaction hash
    pass

@app.get("/api/wallet/balance")
async def get_balance():
    """Get wallet USDC and MATIC balance"""
    pass

@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    """Real-time updates for new recommendations"""
    pass
```

#### Component 2: Streamlit Dashboard (MVP)
```python
# frontend/streamlit_app.py
import streamlit as st
import requests

st.set_page_config(page_title="Polymarket AI Trader", layout="wide")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    wallet_address = st.text_input("Wallet Address")
    auto_execute = st.checkbox("Auto-execute trades")

# Main dashboard
col1, col2 = st.columns(2)

with col1:
    st.metric("USDC Balance", "$1,234.56")
    st.metric("Active Positions", "3")

with col2:
    st.metric("Total P&L", "+$127.45", delta="+12.3%")
    st.metric("Win Rate", "67%")

# Recommendation card
st.header("🤖 Current Recommendation")
rec = requests.get("http://localhost:8000/api/recommendation").json()

st.subheader(rec["market"]["question"])
st.write(f"**AI Prediction:** {rec['prediction']}%")
st.write(f"**Current Price:** {rec['current_price']}%")
st.write(f"**Edge:** +{rec['edge']}%")

col1, col2, col3 = st.columns(3)
if col1.button("✅ Execute Trade", type="primary"):
    # Execute trade
    st.success("Trade executed!")
if col2.button("🔄 Get New Recommendation"):
    st.rerun()
if col3.button("❌ Skip"):
    st.info("Skipped recommendation")
```

---

## Phase 4: Enhanced Features (Add Over Time)

### Week 1: Core Functionality
- ✅ Display latest recommendation
- ✅ Show wallet balance
- ✅ Manual refresh button
- ✅ Execute trade button (with confirmation)

### Week 2: Real-Time Updates
- ✅ Background thread running trader
- ✅ Auto-refresh every 30s
- ✅ Notification when new recommendation
- ✅ Progress indicators

### Week 3: Trade Execution
- ✅ Confirmation dialog
- ✅ Slippage protection
- ✅ Transaction status tracking
- ✅ Success/error messages

### Week 4: History & Analytics
- ✅ Trade history table
- ✅ P&L tracking
- ✅ Win rate statistics
- ✅ Charts (plotly)

### Future Enhancements
- Multiple recommendations at once
- Market comparison view
- Custom risk parameters
- Export trade history

---

## Phase 5: Local Server Deployment

### Development Mode
```bash
# Terminal 1: Keep this running
cd agents
streamlit run gui/app.py
```

### Production Mode (Always Running)
**Option 1: Windows Service (Recommended)**
```bash
# Install NSSM (Non-Sucking Service Manager)
choco install nssm

# Create service
nssm install PolymarketTraderGUI "C:\path\to\python.exe" "C:\path\to\streamlit" "run" "gui/app.py"
nssm start PolymarketTraderGUI
```

**Option 2: Startup Script**
Create `start_trader_gui.bat`:
```batch
@echo off
cd C:\Users\user\OneDrive\Desktop\polymarket\agents
call .venv\Scripts\activate.bat
streamlit run gui/app.py
```
Add to Windows Startup folder

**Option 3: Docker (Cleanest)**
```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt streamlit plotly pandas
EXPOSE 8501
CMD ["streamlit", "run", "gui/app.py", "--server.address", "0.0.0.0"]
```

```bash
docker build -t polymarket-gui .
docker run -p 8501:8501 -v $(pwd):/app polymarket-gui
```

---

## Phase 6: Timeline (Realistic for Local)

### Day 1 (Today - 2 hours)
- [ ] Install Streamlit
- [ ] Create basic `gui/app.py`
- [ ] Test showing recommendation
- [ ] Verify wallet balance display

### Day 2 (Tomorrow - 3 hours)
- [ ] Add "Get Recommendation" button
- [ ] Integrate with Trader class
- [ ] Show AI analysis
- [ ] Add trade execution button (stub)

### Day 3 (1-2 hours)
- [ ] Implement actual trade execution
- [ ] Add confirmation dialog
- [ ] Test end-to-end flow
- [ ] Error handling

### Day 4 (2 hours)
- [ ] Add trade history view
- [ ] Create stats dashboard
- [ ] Polish UI
- [ ] Add auto-refresh

### Day 5 (1 hour)
- [ ] Set up as Windows service
- [ ] Configure auto-start
- [ ] Final testing
- [ ] Done! ✅

**Total: ~10 hours over 5 days**

---

## Phase 7: Simplified File Structure

```
agents/
├── gui/                           # NEW GUI FOLDER
│   ├── app.py                     # Main Streamlit app (300 lines)
│   ├── components/
│   │   ├── dashboard.py           # Dashboard widgets
│   │   ├── recommendation.py      # Recommendation card
│   │   └── trade_history.py       # History table
│   └── utils.py                   # Helper functions
│
├── agents/                        # Existing code
│   ├── application/
│   │   └── trade.py              # Modified with GUI hooks
│   ├── polymarket/
│   └── ...
│
├── trade_recommendation_*.json    # Output files
├── trades.db                      # SQLite for history (NEW)
└── requirements.txt               # Add streamlit, plotly
```

---

## Phase 8: Security (Even for Local)

### Minimal Security Measures
Since it's local-only, we still want:
1. ✅ **Confirmation before trades** - Big obvious button
2. ✅ **Position limits** - Max 20% of balance per trade
3. ✅ **Emergency stop** - Red button to pause all trading
4. ✅ **Transaction logging** - Audit trail in SQLite

### What We DON'T Need (Local Only)
- ❌ Authentication/passwords (it's your machine)
- ❌ HTTPS/SSL (localhost is safe)
- ❌ Rate limiting (you control usage)
- ❌ API keys in secrets manager (use .env file)

---

## Quick Start Commands

```bash
# Setup (5 minutes)
cd agents
pip install streamlit plotly pandas

# Create GUI
mkdir gui
cd gui
# Create app.py (copy from Phase 3 above)

# Run
streamlit run app.py

# Browser auto-opens to:
# http://localhost:8501
```

---

## Next Steps

**Want me to create the actual `gui/app.py` file right now?**

I can build the complete working GUI in the next 10 minutes:
1. Create `gui/` folder
2. Write `app.py` with all the basic features
3. Install Streamlit
4. Run it and show you the result

Ready to start? 🚀
