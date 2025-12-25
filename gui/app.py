import streamlit as st
import sys
import os
import json
import glob
from datetime import datetime
import threading
import time
import asyncio
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("=" * 80)
print("🚀 STARTING POLYMARKET APP")
print("=" * 80)

# Fix for asyncio event loop issue in Streamlit
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("📦 Loading modules...")
try:
    from agents.application.trade import Trader
    print("✅ Loaded Trader")
except Exception as e:
    print(f"❌ Failed to load Trader: {e}")
    raise

try:
    from agents.polymarket.polymarket import Polymarket
    print("✅ Loaded Polymarket")
except Exception as e:
    print(f"❌ Failed to load Polymarket: {e}")
    raise

try:
    from agents.polymarket.gamma import GammaMarketClient
    print("✅ Loaded GammaMarketClient")
except Exception as e:
    print(f"❌ Failed to load GammaMarketClient: {e}")
    raise

try:
    from automated_trader.bot_controller import BotController
    print("✅ Loaded BotController")
except Exception as e:
    print(f"❌ Failed to load BotController: {e}")
    raise

try:
    from automated_trader import config
    print("✅ Loaded config")
except Exception as e:
    print(f"❌ Failed to load config: {e}")
    raise

print("📋 All modules loaded successfully!")
print("=" * 80)

# Page config
st.set_page_config(
    page_title="Polymarket AI Trader",
    layout="wide",
    page_icon="🤖",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .recommendation-card {
        background-color: #e8f4f8;
        padding: 25px;
        border-radius: 15px;
        border-left: 5px solid #1f77b4;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
print("🔧 Initializing session state...")
try:
    if 'trader' not in st.session_state:
        print("  Creating Trader...")
        st.session_state.trader = Trader()
        print("  ✅ Trader created")
    
    if 'polymarket' not in st.session_state:
        print("  Creating Polymarket client...")
        st.session_state.polymarket = Polymarket()
        print("  ✅ Polymarket client created")
    
    if 'gamma' not in st.session_state:
        print("  Creating Gamma client...")
        st.session_state.gamma = GammaMarketClient()
        print("  ✅ Gamma client created")
    
    if 'bot_controller' not in st.session_state:
        print("  Creating BotController...")
        st.session_state.bot_controller = BotController(st.session_state.gamma, st.session_state.polymarket)
        print("  ✅ BotController created")
    
    if 'running_recommendation' not in st.session_state:
        st.session_state.running_recommendation = False
    if 'last_recommendation' not in st.session_state:
        st.session_state.last_recommendation = None
    if 'num_recommendations' not in st.session_state:
        st.session_state.num_recommendations = 10
    
    print("✅ Session state initialized!")
except Exception as e:
    print(f"❌ ERROR during initialization: {e}")
    import traceback
    traceback.print_exc()
    st.error(f"❌ Initialization failed: {str(e)}")
    st.stop()

# Header
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    st.markdown("<h1 style='text-align: center;'>🤖 Polymarket Autonomous Trader</h1>", unsafe_allow_html=True)
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("💼 Wallet")
    
    try:
        address = st.session_state.polymarket.get_active_address()
        st.code(f"{address[:6]}...{address[-4:]}", language=None)
        
        usdc_balance = st.session_state.polymarket.get_usdc_balance()
        st.metric("USDC Balance", f"${usdc_balance:.2f}", delta=None)
    except Exception as e:
        st.warning("⚠️ Could not fetch wallet info")
        st.caption(f"Error: {str(e)}")
    
    st.markdown("---")
    
    st.header("⚙️ Settings")
    auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
    
    st.markdown("---")
    
    st.header("ℹ️ Status")
    st.success("✅ Connected")
    st.caption(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
    
    if st.button("🔄 Refresh Page", use_container_width=True):
        st.rerun()

# Main content
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🤖 Automated Trading", "📊 AI Recommendations", "🔍 Browse Markets", "💼 My Positions", "📜 History", "🔧 Advanced"])

with tab1:
    st.header("🤖 Automated Trading Bot")
    st.markdown("Rule-based algorithmic trader - no AI, pure mathematics")
    
    # Get bot status
    bot = st.session_state.bot_controller
    status = bot.get_status()
    
    # Control Panel
    st.subheader("🎮 Control Panel")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if status['is_running']:
            if st.button("⏸️ Stop Bot", type="secondary", use_container_width=True):
                success, message = bot.stop()
                if success:
                    st.success(message)
                else:
                    st.error(message)
                time.sleep(0.5)
                st.rerun()
        else:
            if st.button("▶️ Start Bot", type="primary", use_container_width=True):
                success, message = bot.start()
                if success:
                    st.success(message)
                else:
                    st.error(message)
                time.sleep(0.5)
                st.rerun()
    
    with col2:
        if status['is_running']:
            st.metric("Status", "🟢 Running")
        else:
            st.metric("Status", "🔴 Stopped")
    
    with col3:
        st.metric("Iterations", status['iteration'])
    
    with col4:
        if status['last_scan']:
            elapsed = (datetime.now() - status['last_scan']).seconds
            st.metric("Last Scan", f"{elapsed}s ago")
        else:
            st.metric("Last Scan", "Never")
    
    st.markdown("---")
    
    # Performance Dashboard
    st.subheader("💰 Performance")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Bankroll", f"${status['bankroll']:.2f}")
    
    with col2:
        daily_pnl = status['daily_pnl']
        st.metric("Daily P&L", f"${daily_pnl:+.2f}", 
                 delta=f"{(daily_pnl/config.INITIAL_BANKROLL*100):+.1f}%")
    
    with col3:
        total_pnl = status['total_pnl']
        st.metric("Total P&L", f"${total_pnl:+.2f}",
                 delta=f"{(total_pnl/config.INITIAL_BANKROLL*100):+.1f}%")
    
    with col4:
        st.metric("Open Positions", f"{status['open_positions']}/{config.MAX_CONCURRENT_POSITIONS}")
    
    with col5:
        deployed_pct = (status['deployed_capital'] / status['bankroll'] * 100) if status['bankroll'] > 0 else 0
        st.metric("Deployed", f"${status['deployed_capital']:.2f}",
                 delta=f"{deployed_pct:.0f}%")
    
    # Risk Status
    col1, col2 = st.columns(2)
    
    with col1:
        if status['trading_halted']:
            st.error(f"🛑 Trading Halted: {status['status_message']}")
        elif status['consecutive_losses'] > 0:
            st.warning(f"⚠️ Consecutive Losses: {status['consecutive_losses']}/{config.MAX_CONSECUTIVE_LOSSES}")
        else:
            st.success("✅ Risk Limits: Normal")
    
    with col2:
        if config.DRY_RUN_MODE:
            st.info("ℹ️ Running in DRY RUN mode - No real trades executed")
        else:
            st.warning("⚠️ LIVE MODE - Real trades will be executed!")
    
    st.markdown("---")
    
    # Open Positions
    st.subheader("📈 Open Positions")
    
    positions = bot.get_positions()
    
    if positions:
        for pos in positions:
            with st.expander(f"{'🟢 YES' if 'YES' in pos['signal'] else '🔴 NO'} | {pos['market_question'][:60]}...", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Entry", f"${pos['entry_price']:.3f}")
                    st.caption(f"Size: ${pos['position_size']:.2f}")
                
                with col2:
                    st.metric("Target", f"${pos['target_price']:.3f}")
                    st.caption(f"+{config.PROFIT_TARGET:.1%}")
                
                with col3:
                    st.metric("Stop", f"${pos['stop_price']:.3f}")
                    st.caption(f"{config.STOP_LOSS_PCT:.1%}")
                
                with col4:
                    hours_open = (datetime.now() - pos['entry_time']).total_seconds() / 3600
                    st.metric("Time Open", f"{hours_open:.1f}h")
                    st.caption(f"Timeout: {config.POSITION_TIMEOUT_HOURS}h")
    else:
        st.info("No open positions")
    
    st.markdown("---")
    
    # Activity Log
    st.subheader("📋 Activity Log")
    
    logs = bot.get_logs(last_n=30)
    
    if logs:
        log_container = st.container(height=300)
        with log_container:
            for log in reversed(logs):
                st.text(log)
    else:
        st.info("No activity yet")
    
    # Performance Stats
    st.markdown("---")
    st.subheader("📊 Performance Statistics")
    
    stats = bot.get_performance_stats()
    
    if stats.get('total_trades', 0) > 0:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Trades", stats['total_trades'])
            st.caption(f"W: {stats['winning_trades']} | L: {stats['losing_trades']}")
        
        with col2:
            st.metric("Win Rate", f"{stats['win_rate']:.1f}%")
        
        with col3:
            st.metric("Avg Win", f"${stats['avg_win']:.2f}")
            st.caption(f"Avg Loss: ${stats['avg_loss']:.2f}")
        
        with col4:
            st.metric("Profit Factor", f"{stats['profit_factor']:.2f}")
    else:
        st.info("No completed trades yet")
    
    # Strategy Configuration
    with st.expander("⚙️ Strategy Configuration", expanded=False):
        st.markdown("**Market Selection:**")
        st.write(f"- Min Total Volume: ${config.MIN_TOTAL_VOLUME:,.0f}")
        st.write(f"- Min 24h Volume: ${config.MIN_24H_VOLUME:,.0f}")
        st.write(f"- Min Hours to Resolution: {config.MIN_HOURS_TO_RESOLUTION} ({config.MIN_HOURS_TO_RESOLUTION/24:.1f} days)")
        
        st.markdown("**Entry/Exit:**")
        st.write(f"- Edge Required: {config.EDGE_REQUIRED:.1%}")
        st.write(f"- Profit Target: {config.PROFIT_TARGET:.1%}")
        st.write(f"- Stop Loss: {config.STOP_LOSS_PCT:.1%}")
        st.write(f"- Position Timeout: {config.POSITION_TIMEOUT_HOURS}h")
        
        st.markdown("**Position Sizing:**")
        st.write(f"- Max Position Size: {config.MAX_POSITION_SIZE_PCT:.1%} of bankroll")
        st.write(f"- Max Deployed: {config.MAX_DEPLOYED_PCT:.1%} of bankroll")
        st.write(f"- Max Concurrent: {config.MAX_CONCURRENT_POSITIONS} positions")
        
        st.markdown("**Risk Management:**")
        st.write(f"- Max Consecutive Losses: {config.MAX_CONSECUTIVE_LOSSES}")
        st.write(f"- Daily Max Loss: {config.DAILY_MAX_LOSS_PCT:.1%} of bankroll")
        
        st.caption("Edit automated_trader/config.py to modify these settings")
    
    # Auto-refresh if running
    if status['is_running']:
        time.sleep(2)
        st.rerun()

with tab2:
    st.subheader("🎯 Smart Recommendations - Algorithmic Analysis")
    
    # Risk status
    bot = st.session_state.bot_controller
    open_positions = bot.get_positions()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Weekly Budget", f"${config.WEEKLY_BUDGET:.0f}", delta=None)
    with col2:
        st.metric("Max Bet", f"${config.MAX_BET_SIZE:.0f}", delta=f"Rec: ${config.DEFAULT_BET_SIZE:.0f}")
    with col3:
        st.metric("Open Positions", f"{len(open_positions)}/{config.MAX_CONCURRENT_POSITIONS}")
    with col4:
        risk_stats = bot.risk_controller.get_stats() if hasattr(bot.risk_controller, 'get_stats') else {}
        weekly_loss = risk_stats.get('weekly_loss', 0) if isinstance(risk_stats, dict) else 0
        st.metric("Weekly Loss Cap", f"${config.WEEKLY_MAX_LOSS:.0f}", delta=f"Used: ${abs(weekly_loss):.0f}")
    
    st.markdown("---")
    
    # Scan button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 Scan Markets Now", type="primary", use_container_width=True):
            st.session_state.scanning = True
            st.rerun()
    with col2:
        st.info(f"**Strategy**: Looking for markets with {config.EDGE_REQUIRED:.0%}+ edge, ${config.MIN_TOTAL_VOLUME:,.0f}+ volume, {config.MIN_HOURS_TO_RESOLUTION/24:.0f}+ days to resolution")
    
    st.markdown("---")
    
    # Scan and analyze markets
    if st.session_state.get('scanning', False):
        with st.spinner("🔍 Scanning markets and analyzing opportunities..."):
            try:
                from automated_trader.market_selector import MarketSelector
                from automated_trader.signal_generator import SignalGenerator
                
                # Get tradeable markets
                selector = MarketSelector(st.session_state.gamma, st.session_state.polymarket)
                signal_gen = SignalGenerator()
                
                markets = selector.get_tradeable_markets()
                
                # Analyze each market for signals
                opportunities = []
                for market in markets:
                    order_book = market.get('order_book')
                    if not order_book:
                        continue
                    
                    fair_value = signal_gen.calculate_fair_value(order_book)
                    if fair_value is None:
                        continue
                    
                    signal, entry_price, signal_reason = signal_gen.generate_entry_signal(market, fair_value)
                    
                    if signal.value in ['BUY_YES', 'BUY_NO']:
                        # Get price data
                        yes_asks = order_book.get('yes', {}).get('asks', [])
                        no_asks = order_book.get('no', {}).get('asks', [])
                        best_yes = min([float(a['price']) for a in yes_asks]) if yes_asks else None
                        best_no = min([float(a['price']) for a in no_asks]) if no_asks else None
                        
                        opportunities.append({
                            'market': market,
                            'signal': signal.value,
                            'entry_price': entry_price,
                            'fair_value': fair_value,
                            'best_yes_price': best_yes,
                            'best_no_price': best_no,
                            'reason': signal_reason,
                            'token_id': market.get('clobTokenIds', ['', ''])[0 if signal.value == 'BUY_YES' else 1] if market.get('clobTokenIds') else None
                        })
                
                st.session_state.opportunities = opportunities
                st.session_state.scanning = False
                st.success(f"✅ Found {len(opportunities)} trading opportunities!")
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error scanning markets: {str(e)}")
                st.session_state.scanning = False
                st.session_state.opportunities = []
    
    # Display opportunities
    opportunities = st.session_state.get('opportunities', [])
    
    if opportunities:
        st.success(f"📊 **{len(opportunities)} Opportunities Found** - Markets with {config.EDGE_REQUIRED:.0%}+ edge detected")
        
        for idx, opp in enumerate(opportunities):
            market = opp['market']
            signal = opp['signal']
            entry_price = opp['entry_price']
            fair_value = opp['fair_value']
            
            # Create card for each opportunity
            with st.container():
                st.markdown(f"### 🎯 Opportunity #{idx+1}")
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**{market.get('question', 'Unknown Market')}**")
                
                with col2:
                    if signal == 'BUY_YES':
                        st.success("✅ BUY YES")
                    else:
                        st.error("❌ BUY NO")
                
                # Market stats
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Fair Value", f"{fair_value:.1%}")
                
                with col2:
                    st.metric("Entry Price", f"${entry_price:.3f}")
                
                with col3:
                    volume = market.get('volume', 0)
                    st.metric("Volume", f"${volume:,.0f}")
                
                with col4:
                    # Calculate time to resolution
                    end_date_str = market.get('endDateIso')
                    if end_date_str:
                        try:
                            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                            now = datetime.now(end_date.tzinfo)
                            hours = (end_date - now).total_seconds() / 3600
                            days = hours / 24
                            st.metric("Time Left", f"{days:.1f} days")
                        except:
                            st.metric("Time Left", "N/A")
                    else:
                        st.metric("Time Left", "N/A")
                
                # Analysis details
                st.info(f"📊 **Analysis**: {opp['reason']}")
                
                # Current prices
                if opp.get('best_yes_price') and opp.get('best_no_price'):
                    st.caption(f"Current Prices: YES ${opp['best_yes_price']:.3f} | NO ${opp['best_no_price']:.3f}")
                
                # Display recommended bet amount (fixed $5)
                bet_amount = config.DEFAULT_BET_SIZE
                
                col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                
                with col1:
                    st.metric("Recommended Bet", f"${bet_amount:.2f}")
                    st.caption(f"Max: ${config.MAX_BET_SIZE:.2f}")
                
                with col2:
                    shares = bet_amount / entry_price if entry_price > 0 else 0
                    st.metric("Shares", f"{shares:.1f}")
                
                with col3:
                    max_profit = bet_amount / entry_price if entry_price > 0 else 0
                    st.metric("Max Profit", f"${max_profit:.2f}")
                
                with col4:
                    roi = (1 / entry_price - 1) * 100 if entry_price > 0 else 0
                    st.metric("Max ROI", f"{roi:.0f}%")
                
                # Check position limits before allowing trade
                open_positions = bot.get_positions() if 'bot' in locals() else []
                can_trade = len(open_positions) < config.MAX_CONCURRENT_POSITIONS
                
                # Action buttons
                btn_col1, btn_col2 = st.columns(2)
                
                with btn_col1:
                    if not can_trade:
                        st.warning(f"⚠️ Max {config.MAX_CONCURRENT_POSITIONS} position limit reached")
                    
                    trade_button = st.button(
                        f"💰 Place {'YES' if signal == 'BUY_YES' else 'NO'} Bet (${bet_amount:.2f})",
                        key=f"place_{idx}",
                        type="primary",
                        use_container_width=True,
                        disabled=not can_trade
                    )
                    
                    if trade_button:
                        # Place the bet
                        with st.spinner(f"Placing ${bet_amount:.2f} bet..."):
                            try:
                                token_id = opp.get('token_id')
                                if not token_id:
                                    # Get token ID from clobTokenIds
                                    clob_ids = market.get('clobTokenIds', [])
                                    if isinstance(clob_ids, str):
                                        import json
                                        clob_ids = json.loads(clob_ids)
                                    
                                    if signal == 'BUY_YES':
                                        token_id = clob_ids[0] if len(clob_ids) > 0 else None
                                    else:
                                        token_id = clob_ids[1] if len(clob_ids) > 1 else None
                                
                                if token_id:
                                    if config.DRY_RUN_MODE:
                                        st.success(f"✅ DRY RUN: Would place ${bet_amount:.2f} {signal.replace('BUY_', '')} bet")
                                        st.info(f"Token ID: {token_id}")
                                        st.warning("🔒 LIVE TRADING LOCKED - Must disable DRY_RUN_MODE in config.py after confirming compliance")
                                    else:
                                        # Check position limits before executing
                                        if len(open_positions) >= config.MAX_CONCURRENT_POSITIONS:
                                            st.error(f"❌ Cannot place trade: Already at max {config.MAX_CONCURRENT_POSITIONS} position limit")
                                        elif bet_amount > config.MAX_BET_SIZE:
                                            st.error(f"❌ Cannot place trade: Bet ${bet_amount:.2f} exceeds max ${config.MAX_BET_SIZE:.2f}")
                                        else:
                                            # Execute real order
                                            response = st.session_state.polymarket.execute_market_order_by_token(token_id, bet_amount)
                                            st.success(f"✅ Order placed! Response: {response}")
                                else:
                                    st.error("❌ Could not find token ID for this market")
                                    
                            except Exception as e:
                                st.error(f"❌ Error placing bet: {str(e)}")
                
                with btn_col2:
                    if st.button(f"ℹ️ View on Polymarket", key=f"view_{idx}", use_container_width=True):
                        condition_id = market.get('conditionId', '')
                        if condition_id:
                            st.markdown(f"[Open Market →](https://polymarket.com/event/{condition_id})")
                
                st.markdown("---")
    
    else:
        # No opportunities yet
        st.info("👆 Click 'Scan Markets Now' to find trading opportunities")
        
        st.markdown("### 📋 How it works:")
        st.markdown(f"""
        **Market Selection Criteria:**
        - ✅ Minimum Volume: ${config.MIN_TOTAL_VOLUME:,.0f}
        - ✅ Minimum 24h Volume: ${config.MIN_24H_VOLUME:,.0f}
        - ✅ Time to Resolution: {config.MIN_HOURS_TO_RESOLUTION/24:.0f}+ days
        - ✅ Maximum Spread: {config.MAX_BID_ASK_SPREAD_PCT:.0%}
        
        **Signal Generation:**
        - 📊 Calculates fair value from order book
        - 🎯 Looks for {config.EDGE_REQUIRED:.0%}+ pricing inefficiency (edge)
        - ✅ Recommends BUY YES if market underpriced vs fair value
        - ❌ Recommends BUY NO if market overpriced vs fair value
        
        **Your Action:**
        - 💰 Fixed ${config.DEFAULT_BET_SIZE:.0f} bet (max ${config.MAX_BET_SIZE:.0f})
        - 🎲 Click to place bet (or view on Polymarket)
        - 📈 Monitor in "My Positions" tab
        """)
        
        with st.expander("⚙️ Current Strategy Settings"):
            st.write(f"**Position Sizing:**")
            st.write(f"- Recommended Bet: ${config.DEFAULT_BET_SIZE:.0f}")
            st.write(f"- Maximum Bet: ${config.MAX_BET_SIZE:.0f}")
            st.write(f"- Max Concurrent: {config.MAX_CONCURRENT_POSITIONS} position")
            st.write(f"- Weekly Budget: ${config.WEEKLY_BUDGET:.0f}")
            st.write(f"- Weekly Loss Cap: ${config.WEEKLY_MAX_LOSS:.0f}")
            
            st.write(f"**Market Filters:**")
            st.write(f"- Edge Required: {config.EDGE_REQUIRED:.0%}")
            st.write(f"- Min Volume: ${config.MIN_TOTAL_VOLUME:,.0f}")
            st.write(f"- Min 24h Volume: ${config.MIN_24H_VOLUME:,.0f}")
            st.write(f"- Min Hours to Resolution: {config.MIN_HOURS_TO_RESOLUTION} ({config.MIN_HOURS_TO_RESOLUTION/24:.0f} days)")
            st.write(f"- Max Spread: {config.MAX_BID_ASK_SPREAD_PCT:.0%}")
            
            st.write(f"**Risk Controls:**")
            st.write(f"- Stop after {config.MAX_CONSECUTIVE_LOSSES} consecutive losses")
            st.write(f"- Pause if weekly loss cap (${config.WEEKLY_MAX_LOSS:.0f}) hit")
            st.caption("Edit automated_trader/config.py to modify settings")

with tab3:
    st.header("� Browse Markets by Category")
    st.markdown("Select a category to see available markets, then pick specific ones for AI analysis")
    
    # Category selection
    col1, col2 = st.columns([2, 3])
    with col1:
        category = st.selectbox(
            "Market Category",
            ["politics", "crypto", "sports", "pop-culture", "business", "science", "all"],
            help="Browse markets by topic"
        )
    with col2:
        st.markdown(f"**Selected:** {category.title()}")
        st.caption("AI will analyze your selected markets and recommend YES or NO positions")
    
    # Load markets
    if st.button("🔄 Load Markets", type="primary", use_container_width=True):
        st.session_state.browsing_markets = True
        st.session_state.selected_category = category
        st.rerun()
    
    if 'browsing_markets' in st.session_state and st.session_state.browsing_markets:
        with st.spinner(f"Loading {category} markets..."):
            try:
                from agents.polymarket.gamma import GammaMarketClient
                gamma = GammaMarketClient()
                
                # Get markets by category
                if category == "all":
                    markets_raw = gamma.get_all_current_markets(limit=50)
                else:
                    markets_raw = gamma.get_markets_by_tag(category, limit=50)
                
                if not markets_raw:
                    st.warning(f"No active markets found in {category}")
                else:
                    st.success(f"Found {len(markets_raw)} markets in {category}")
                    
                    # Display markets as selectable cards
                    st.markdown("---")
                    st.markdown("### 📋 Select Markets for AI Analysis")
                    
                    # Initialize selection state
                    if 'selected_markets' not in st.session_state:
                        st.session_state.selected_markets = []
                    
                    for idx, market in enumerate(markets_raw):
                        # Handle market as dict
                        question = market.get('question', 'Unknown')
                        market_id = market.get('id', idx)
                        outcomes = market.get('outcomes', [])
                        if isinstance(outcomes, str):
                            import json
                            try:
                                outcomes = json.loads(outcomes)
                            except:
                                outcomes = []
                        
                        with st.expander(f"{'✅' if idx in st.session_state.selected_markets else '⬜'} {question[:100]}...", expanded=False):
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.markdown(f"**Question:** {question}")
                                st.caption(f"Outcomes: {', '.join(outcomes)}")
                                
                                # Show current prices
                                outcome_prices = market.get('outcomePrices', [])
                                if isinstance(outcome_prices, str):
                                    try:
                                        outcome_prices = json.loads(outcome_prices)
                                    except:
                                        outcome_prices = []
                                        
                                if outcome_prices and outcomes:
                                    price_str = " | ".join([f"{outcome}: ${float(price):.4f}" for outcome, price in zip(outcomes, outcome_prices)])
                                    st.info(f"💰 Current prices: {price_str}")
                                
                                end_date = market.get('endDateIso') or market.get('endDate', 'N/A')
                                st.caption(f"📅 Ends: {end_date[:10] if isinstance(end_date, str) else 'N/A'}")
                            
                            with col2:
                                # Selection checkbox
                                is_selected = idx in st.session_state.selected_markets
                                if st.button(f"{'✅ Selected' if is_selected else '➕ Select'}", key=f"select_{idx}_{market_id}", use_container_width=True):
                                    if is_selected:
                                        st.session_state.selected_markets.remove(idx)
                                    else:
                                        st.session_state.selected_markets.append(idx)
                                    st.rerun()
                    
                    # Get recommendations for selected markets
                    if st.session_state.selected_markets:
                        st.markdown("---")
                        st.success(f"🎯 {len(st.session_state.selected_markets)} markets selected")
                        
                        if st.button("🤖 Get AI Recommendations for Selected Markets", type="primary", use_container_width=True):
                            st.session_state.analyzing_selected = True
                            st.rerun()
                        
                        if 'analyzing_selected' in st.session_state and st.session_state.analyzing_selected:
                            with st.spinner("AI analyzing your selected markets..."):
                                try:
                                    # Convert selected markets to format needed by trader
                                    from langchain_community.vectorstores.utils import Document
                                    import ast
                                    
                                    recommendations = []
                                    for idx in st.session_state.selected_markets:
                                        market = markets_raw[idx]
                                        
                                        # Parse outcomes and prices
                                        outcomes = market.get('outcomes', [])
                                        if isinstance(outcomes, str):
                                            outcomes = json.loads(outcomes)
                                        
                                        outcome_prices = market.get('outcomePrices', [])
                                        if isinstance(outcome_prices, str):
                                            outcome_prices = json.loads(outcome_prices)
                                        
                                        clob_token_ids = market.get('clobTokenIds', [])
                                        if isinstance(clob_token_ids, str):
                                            clob_token_ids = json.loads(clob_token_ids)
                                        
                                        # Create market document in the format trader expects
                                        market_doc = Document(
                                            page_content=market.get('description', market.get('question', '')),
                                            metadata={
                                                "question": market.get('question', ''),
                                                "outcomes": str(outcomes),
                                                "outcome_prices": str(outcome_prices),
                                                "clob_token_ids": str(clob_token_ids)
                                            }
                                        )
                                        
                                        # Get AI recommendation
                                        rec = st.session_state.trader.get_recommendation_for_market([market_doc], execute=False)
                                        recommendations.append(rec)
                                    
                                    # Save and display
                                    st.session_state.trader._save_multiple_recommendations(recommendations, False)
                                    st.session_state.analyzing_selected = False
                                    st.session_state.browsing_markets = False
                                    st.success(f"✅ Generated {len(recommendations)} recommendations! Check the AI Recommendations tab")
                                    st.balloons()
                                    
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                                    st.session_state.analyzing_selected = False
                    
            except Exception as e:
                st.error(f"Error loading markets: {str(e)}")
                st.session_state.browsing_markets = False

with tab4:
    st.header("�💼 My Positions")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### Active Bets & Payouts")
    with col2:
        if st.button("🔄 Refresh Positions", use_container_width=True):
            st.rerun()
    
    # Get user positions
    with st.spinner("Loading your positions..."):
        try:
            positions = st.session_state.polymarket.get_user_positions()
            
            if not positions:
                st.info("📭 You don't have any active positions yet. Place your first bet from the Dashboard!")
                st.markdown("""
                **How it works:**
                - Make bets using the recommendations on the Dashboard
                - Your active positions will appear here
                - When markets resolve, winnings are automatically sent to your wallet
                - Track your performance and see your total P&L
                """)
            else:
                # Summary stats
                total_shares = sum([p['balance'] for p in positions])
                active_positions = [p for p in positions if p['active'] and not p['closed']]
                resolved_positions = [p for p in positions if p['closed']]
                
                # Metrics row
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Active Bets", len(active_positions))
                with col2:
                    st.metric("Total Shares", f"{total_shares:.2f}")
                with col3:
                    st.metric("Resolved Bets", len(resolved_positions))
                with col4:
                    # Estimate potential payout (if all win)
                    max_payout = total_shares * 1.0  # Each share pays $1
                    st.metric("Max Payout", f"${max_payout:.2f}")
                
                st.markdown("---")
                
                # Active Positions
                if active_positions:
                    st.markdown("### 🎲 Active Positions")
                    
                    for idx, pos in enumerate(active_positions):
                        with st.expander(f"📍 {pos['market_question'][:80]}...", expanded=(idx < 3)):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown(f"**Your Shares:** {pos['balance']:.2f}")
                                st.markdown(f"**Potential Payout:** ${pos['balance']:.2f}")
                                
                                # Parse outcomes and show which one user has
                                try:
                                    outcomes = ast.literal_eval(pos['outcomes'])
                                    prices = ast.literal_eval(pos['outcome_prices'])
                                    token_ids = ast.literal_eval(str(pos.get('token_id', '[]')))
                                    
                                    # Show current market prices
                                    st.markdown(f"**Current Prices:**")
                                    for i, outcome in enumerate(outcomes):
                                        price = prices[i] if i < len(prices) else 0
                                        st.write(f"  {outcome}: ${price:.4f}")
                                except:
                                    pass
                            
                            with col2:
                                st.markdown(f"**Market ID:** {pos['market_id']}")
                                st.markdown(f"**End Date:** {pos['end_date'][:10] if pos['end_date'] else 'N/A'}")
                                st.markdown(f"**Status:** {'🟢 Active' if pos['active'] else '⏸️  Paused'}")
                                
                                # Calculate current value
                                try:
                                    prices = ast.literal_eval(pos['outcome_prices'])
                                    avg_price = sum(prices) / len(prices) if prices else 0
                                    current_value = pos['balance'] * avg_price
                                    st.markdown(f"**Current Value:** ${current_value:.2f}")
                                except:
                                    st.markdown(f"**Current Value:** N/A")
                            
                            st.caption(f"💡 If your outcome wins, you'll receive **${pos['balance']:.2f}** (each share pays $1)")
                
                # Resolved Positions
                if resolved_positions:
                    st.markdown("---")
                    st.markdown("### ✅ Resolved Positions")
                    
                    for pos in resolved_positions:
                        with st.expander(f"🏁 {pos['market_question'][:80]}..."):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown(f"**Your Shares:** {pos['balance']:.2f}")
                                st.markdown(f"**Market ID:** {pos['market_id']}")
                            
                            with col2:
                                st.markdown(f"**Status:** ✅ Resolved")
                                # Note: determining win/loss requires knowing which outcome won
                                # This would need additional API call to get market resolution
                                st.caption("Check your wallet for any winnings")
        
        except Exception as e:
            st.error(f"❌ Error loading positions: {str(e)}")
            st.caption("Try refreshing the page or check your wallet connection")

with tab5:
    st.header("📜 Trade History")
    st.info("Trade history tracking coming soon! Will show all executed trades, P&L, and win rate.")
    
    # Placeholder for future trade history
    st.markdown("""
    **Upcoming features:**
    - ✅ All executed trades
    - 📈 Profit & Loss tracking
    - 🎯 Win rate statistics
    - 📊 Performance charts
    - 📥 Export to CSV
    """)

with tab6:
    st.header("🔧 Advanced Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Trading Parameters")
        max_position_size = st.slider("Max Position Size (%)", 1, 100, 20)
        st.caption("Maximum % of balance to risk per trade")
        
        min_edge = st.slider("Minimum Edge (%)", 0, 50, 5)
        st.caption("Minimum predicted edge to recommend a trade")
        
        auto_execute = st.checkbox("Auto-execute trades (DANGEROUS)", value=False)
        st.caption("⚠️ Only enable if you fully trust the AI")
    
    with col2:
        st.subheader("AI Configuration")
        st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
        st.caption("Your OpenAI API key (already set in .env)")
        
        model = st.selectbox("AI Model", ["gpt-3.5-turbo-16k", "gpt-4-1106-preview"])
        st.caption("More advanced models = better predictions = higher cost")
        
        refresh_interval = st.number_input("Refresh Interval (minutes)", 1, 60, 30)
        st.caption("How often to check for new opportunities")
    
    st.markdown("---")
    
    if st.button("💾 Save Settings"):
        st.success("✅ Settings saved (feature coming soon)")

# Auto-refresh logic
if auto_refresh and not st.session_state.running_recommendation:
    time.sleep(30)
    st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <small>🤖 Polymarket Autonomous Trader | Built with Streamlit | ⚠️ Use at your own risk</small><br>
    <small>⚖️ Ensure you comply with <a href='https://polymarket.com/tos' target='_blank'>Polymarket Terms of Service</a></small>
</div>
""", unsafe_allow_html=True)
