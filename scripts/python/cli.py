import typer
from devtools import pprint

from agents.polymarket.polymarket import Polymarket
from agents.connectors.chroma import PolymarketRAG
from agents.connectors.news import News
from agents.application.trade import Trader
from agents.application.executor import Executor
from agents.application.creator import Creator

app = typer.Typer()
# Lazy load clients to avoid credential requirements for help
polymarket = None
newsapi_client = None
polymarket_rag = None

def get_polymarket():
    global polymarket
    if polymarket is None:
        polymarket = Polymarket()
    return polymarket

def get_newsapi_client():
    global newsapi_client
    if newsapi_client is None:
        newsapi_client = News()
    return newsapi_client

def get_polymarket_rag():
    global polymarket_rag
    if polymarket_rag is None:
        polymarket_rag = PolymarketRAG()
    return polymarket_rag


@app.command()
def init_approvals() -> None:
    """
    Initialize token approvals on Polygon (USDC + CTF).
    Only run if you understand and comply with Polymarket TOS.
    """
    pm = get_polymarket()
    print("Submitting approval transactions (USDC approve + CTF setApprovalForAll)...")
    try:
        # Uses the existing private method to send approval txs
        pm._init_approvals(True)
        print("Approvals submitted. It may take ~30-60s to confirm.")
    except Exception as e:
        print(f"Approvals failed: {e}")
        print("Tip: Ensure you have MATIC for gas and try again.")


@app.command()
def check_usdc_balance() -> None:
    """
    Show current USDC balance for the configured wallet.
    """
    pm = get_polymarket()
    addr = pm.get_active_address()
    bal = pm.get_usdc_balance()
    print(f"Active Wallet: {addr}")
    print(f"USDC Balance: {bal:.2f}")


@app.command()
def check_matic_balance() -> None:
    """
    Show current MATIC balance for the configured wallet.
    """
    from web3 import Web3
    pm = get_polymarket()
    addr = pm.get_active_address()
    w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
    bal = w3.eth.get_balance(addr) / 1e18
    print(f"Wallet: {addr}")
    print(f"MATIC Balance: {bal:.6f}")


@app.command()
def check_address_balance(address: str) -> None:
    """
    Show MATIC, native USDC, and USDC.e (bridged) balances for any Polygon address.
    """
    from web3 import Web3
    pm = get_polymarket()
    w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
    addr = Web3.to_checksum_address(address)
    # MATIC
    matic = w3.eth.get_balance(addr) / 1e18
    # USDC (native - Polymarket uses this)
    usdc_native_contract = w3.eth.contract(
        address=Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"),
        abi=[{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
    )
    usdc_native = usdc_native_contract.functions.balanceOf(addr).call() / 1e6
    # USDC.e (bridged - Coinbase often sends this)
    usdc_bridged_contract = w3.eth.contract(
        address=Web3.to_checksum_address("0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"),
        abi=[{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
    )
    usdc_bridged = usdc_bridged_contract.functions.balanceOf(addr).call() / 1e6
    print(f"Address: {addr}")
    print(f"MATIC: {matic:.6f}")
    print(f"USDC (native/Polymarket): ${usdc_native:.2f}")
    print(f"USDC.e (bridged/Coinbase): ${usdc_bridged:.2f}")
    print(f"Total USDC: ${usdc_native + usdc_bridged:.2f}")


@app.command()
def place_market_order_by_token(token_id: str, amount: float) -> None:
    """
    Place a market (FOK) order by `token_id` with `amount` USDC.
    Requires approvals + sufficient USDC. Comply with Polymarket TOS.
    """
    pm = get_polymarket()
    addr = pm.get_address_for_private_key()
    print(f"Placing market order for wallet: {addr}")
    print(f"Token: {token_id} | Amount: {amount}")
    resp = pm.execute_market_order_by_token(token_id=token_id, amount=amount)
    print(f"Response: {resp}")


@app.command()
def get_all_markets(limit: int = 10, sort_by: str = "volume", min_liquidity: float = 1000.0) -> None:
    """
    Query Polymarket's current active markets
    """
    print(f"Fetching top {limit} markets sorted by {sort_by} (min liquidity: ${min_liquidity:,.0f})")
    markets = get_polymarket().get_all_markets()
    markets = get_polymarket().filter_markets_for_trading(markets)
    
    # Filter for markets with actual liquidity and trading activity
    markets = [m for m in markets if m.funded or float(m.rewardsMinSize) > 0]
    
    # Sort by different criteria
    if sort_by == "volume":
        # Markets with higher spread often indicate more activity
        markets = sorted(markets, key=lambda x: x.spread, reverse=False)
    elif sort_by == "spread":
        markets = sorted(markets, key=lambda x: x.spread, reverse=True)
    else:
        markets = sorted(markets, key=lambda x: x.spread, reverse=False)
    
    markets = markets[:limit]
    
    print(f"\n🎯 Found {len(markets)} active markets:\n")
    for i, m in enumerate(markets, 1):
        print(f"{i}. {m.question}")
        print(f"   Ends: {m.end}")
        print(f"   Spread: {m.spread:.4f} | Funded: {m.funded}")
        print(f"   Outcomes: {m.outcomes}")
        print()
    
    pprint(markets)


@app.command()
def find_market_tokens(keyword: str, limit: int = 5) -> None:
    """
    Search markets by keyword and print their `clob_token_ids` for trading.
    """
    pm = get_polymarket()
    markets = pm.get_all_markets()
    markets = pm.filter_markets_for_trading(markets)
    matches = [m for m in markets if keyword.lower() in m.question.lower()]
    print(f"Found {len(matches)} matches for '{keyword}':\n")
    for m in matches[:limit]:
        print(f"Question: {m.question}")
        print(f"Ends: {m.end} | Spread: {m.spread:.4f} | Funded: {m.funded}")
        print(f"Outcomes: {m.outcomes}")
        print(f"Token IDs: {m.clob_token_ids}")
        print()


@app.command()
def get_relevant_news(keywords: str) -> None:
    """
    Use NewsAPI to query the internet
    """
    articles = get_newsapi_client().get_articles_for_cli_keywords(keywords)
    pprint(articles)


@app.command()
def get_all_events(limit: int = 5, sort_by: str = "number_of_markets") -> None:
    """
    Query Polymarket's events
    """
    print(f"limit: int = {limit}, sort_by: str = {sort_by}")
    events = get_polymarket().get_all_events()
    events = get_polymarket().filter_events_for_trading(events)
    if sort_by == "number_of_markets":
        events = sorted(events, key=lambda x: len(x.markets), reverse=True)
    events = events[:limit]
    pprint(events)


@app.command()
def create_local_markets_rag(local_directory: str) -> None:
    """
    Create a local markets database for RAG
    """
    get_polymarket_rag().create_local_markets_rag(local_directory=local_directory)


@app.command()
def query_local_markets_rag(vector_db_directory: str, query: str) -> None:
    """
    RAG over a local database of Polymarket's events
    """
    response = get_polymarket_rag().query_local_markets_rag(
        local_directory=vector_db_directory, query=query
    )
    pprint(response)


@app.command()
def ask_superforecaster(event_title: str, market_question: str, outcome: str) -> None:
    """
    Ask a superforecaster about a trade
    """
    print(
        f"event: str = {event_title}, question: str = {market_question}, outcome (usually yes or no): str = {outcome}"
    )
    executor = Executor()
    response = executor.get_superforecast(
        event_title=event_title, market_question=market_question, outcome=outcome
    )
    print(f"Response:{response}")


@app.command()
def create_market() -> None:
    """
    Format a request to create a market on Polymarket
    """
    c = Creator()
    market_description = c.one_best_market()
    print(f"market_description: str = {market_description}")


@app.command()
def ask_llm(user_input: str) -> None:
    """
    Ask a question to the LLM and get a response.
    """
    executor = Executor()
    response = executor.get_llm_response(user_input)
    print(f"LLM Response: {response}")


@app.command()
def ask_polymarket_llm(user_input: str) -> None:
    """
    What types of markets do you want trade?
    """
    executor = Executor()
    response = executor.get_polymarket_llm(user_input=user_input)
    print(f"LLM + current markets&events response: {response}")


@app.command()
def run_autonomous_trader(execute: bool = False) -> None:
    """
    Compute a best trade and optionally execute it.
    Set --execute true only if you comply with Polymarket TOS.
    """
    trader = Trader()
    trader.one_best_trade(execute=execute)


if __name__ == "__main__":
    app()
