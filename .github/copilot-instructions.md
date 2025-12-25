# Polymarket Agents - AI Coding Agent Instructions

## Project Overview
Autonomous trading framework for Polymarket prediction markets using AI agents, LangChain, and RAG (Retrieval-Augmented Generation). Built on Polygon blockchain with Python 3.9. The project enables AI-driven market analysis, news aggregation, and autonomous trade execution on Polymarket's CLOB (Central Limit Order Book).

## Architecture & Core Components

### Module Structure (3-Layer Design)
- **`agents/polymarket/`**: Blockchain/API integration layer
  - `polymarket.py`: Main client wrapping py-clob-client for CLOB operations, Web3 for Polygon transactions, USDC/CTF approvals, balance checking
  - `gamma.py`: Gamma API client for market/event metadata (read-only, parses nested Pydantic models)
- **`agents/application/`**: Business logic layer
  - `trade.py`: `Trader` orchestration - implements `one_best_trade()` strategy with RAG filtering
  - `executor.py`: `Executor` wraps LangChain LLM calls, handles token estimation/chunking, prompt management
  - `prompts.py`: Prompt templates (superforecaster, sentiment analyzer, market analyst)
  - `creator.py`: Market creation utilities
  - `cron.py`: Scheduled task execution
- **`agents/connectors/`**: External data sourcing
  - `chroma.py`: ChromaDB RAG for vectorizing events/markets/news (uses OpenAI embeddings)
  - `news.py`: NewsAPI integration with keyword/category filtering
  - `search.py`: Web search integration (Tavily API)
- **`scripts/python/`**: User interfaces
  - `cli.py`: Typer-based CLI with 16+ commands, lazy client loading (main entry point)
  - `server.py`: FastAPI dashboard at `:8888` for market visualization (dark theme, top 20 markets by spread)
  - `setup.py`: Environment initialization

### Data Models (`agents/utils/objects.py`)
Pydantic models for type safety: `SimpleMarket`, `SimpleEvent`, `Trade`, `Market`, `PolymarketEvent`, `ClobReward`, `Tag`, `Article`

## Critical Development Workflows

### Environment Setup
```bash
# Required Python version (3.9 only - do not use 3.10+)
virtualenv --python=python3.9 .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt  # Use this file (not requirements_clean.txt or requirements_temp.txt)

# Environment variables (.env required)
POLYGON_WALLET_PRIVATE_KEY=""  # Polygon wallet private key (no 0x prefix)
OPENAI_API_KEY=""              # For LLM operations (required)
TAVILY_API_KEY=""              # Optional: web search integration
NEWSAPI_API_KEY=""             # Optional: news data sourcing

# Optional wallet address overrides (display/read-only)
POLYGON_WALLET_ADDRESS=""      # Fallback priority: POLYGON > Coinbase > COINBASE
```

### Running Code
**CRITICAL**: Always set `PYTHONPATH` when running outside Docker:
```bash
# Windows PowerShell (semicolon for chaining, not &&)
$env:PYTHONPATH = "."; python scripts/python/cli.py --help

# Linux/macOS
export PYTHONPATH="."; python scripts/python/cli.py --help

# Running with venv activation
.venv\Scripts\Activate.ps1; $env:PYTHONPATH = "."; python scripts/python/cli.py get-all-markets
```

### CLI Commands (Main Interface - 16 Commands)
```bash
# Wallet/Balance Operations
python scripts/python/cli.py init-approvals                    # Initialize USDC + CTF approvals (one-time setup)
python scripts/python/cli.py check-usdc-balance                # Show USDC balance for configured wallet
python scripts/python/cli.py check-matic-balance               # Show MATIC balance (gas token)
python scripts/python/cli.py check-address-balance <address>   # Check USDC (native + bridged) + MATIC for any address

# Market Discovery & Trading
python scripts/python/cli.py get-all-markets --limit 10 --sort-by volume --min-liquidity 1000
python scripts/python/cli.py find-market-tokens "Trump" --limit 5   # Search markets + get clob_token_ids
python scripts/python/cli.py place-market-order-by-token <token_id> <amount_usdc>  # Execute FOK order

# News & Context Gathering
python scripts/python/cli.py get-relevant-news "election,politics"  # NewsAPI keyword search

# Events & Market Metadata
python scripts/python/cli.py get-all-events --limit 5 --sort-by number_of_markets

# RAG (Vector Database) Operations
python scripts/python/cli.py create-local-markets-rag ./local_db      # Create ChromaDB from current markets
python scripts/python/cli.py query-local-markets-rag ./local_db "climate markets"

# LLM Interactions
python scripts/python/cli.py ask-llm "What are prediction markets?"
python scripts/python/cli.py ask-polymarket-llm "Find markets about AI safety"
python scripts/python/cli.py ask-superforecaster "2024 Election" "Trump wins" "yes"

# Autonomous Trading
python scripts/python/cli.py run-autonomous-trader              # Dry-run (no execution)
python scripts/python/cli.py run-autonomous-trader --execute    # Execute trade (TOS compliance required)

# Market Creation
python scripts/python/cli.py create-market   # Format market creation request
```

### FastAPI Dashboard
```bash
# Start server (default port 8888, can override with --port)
python scripts/python/server.py

# Access at http://localhost:8888
# Shows top 20 markets sorted by spread (lower = better liquidity)
# Dark theme UI with market questions, outcomes, end dates, funding status
```

### Docker Workflow
```bash
./scripts/bash/build-docker.sh      # Build Python 3.9 image
./scripts/bash/run-docker-dev.sh    # Run with volume mounts
./scripts/bash/run-docker.sh        # Production run
```

## Project-Specific Conventions

### Blockchain Integration Patterns
1. **Web3 Initialization**: Uses POA (Proof of Authority) middleware for Polygon compatibility:
   ```python
   self.web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
   ```
2. **Token Approvals**: Two-step approval process required before trading:
   - USDC approval: `usdc.functions.approve(exchange_address, MAX_INT)` for `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E`
   - CTF approval: `ctf.functions.setApprovalForAll(exchange_address, True)` for `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045`
   - Run once via `cli.py init-approvals` or `_init_approvals(True)` in code
3. **USDC Variants**: Handle both native USDC (`0x2791...4174`) and bridged USDC.e (`0x3c49...3359`). Polymarket uses **native USDC**.
4. **API Authentication**: CLOB API uses EIP-712 derived credentials from private key via `create_or_derive_api_creds()` - no separate API key needed
5. **Balance Checking**: Use `get_usdc_balance()` for active wallet, `check_address_balance()` CLI command for any address

### LLM Integration Patterns
1. **Token Management**: 
   - Executor estimates tokens using heuristic: `len(text) // 4` characters per token
   - Chunks data to stay under model limits: 15k tokens for `gpt-3.5-turbo-16k`, 95k for `gpt-4-1106-preview`
   - Configured in `Executor.__init__()` with `max_token_model` dict
2. **Lazy Loading**: CLI uses global singletons (`get_polymarket()`, `get_newsapi_client()`, `get_polymarket_rag()`) initialized on first use to avoid credential requirements for `--help` commands
3. **Prompt Structure**: Always use LangChain message pattern:
   ```python
   system_message = SystemMessage(content=str(self.prompter.method()))
   human_message = HumanMessage(content=user_input)
   messages = [system_message, human_message]
   result = self.llm.invoke(messages)
   ```
4. **LLM Model Selection**: Default is `gpt-3.5-turbo-16k` for cost efficiency; switch to `gpt-4-1106-preview` for complex reasoning

### RAG (Vector Database) Patterns
1. **Local DB Creation**: Creates timestamped JSON dumps then vectorizes:
   - `local_db/all-current-markets_{timestamp}.json` 
   - `local_db_events/` and `local_db_markets/` for separate storage
   - Cleanup via `Trader.clear_local_dbs()` removes all three directories before each trade run
2. **Embedding Model**: Standardized on OpenAI `text-embedding-3-small` for all ChromaDB operations
3. **Windows Compatibility**: Uses Python JSON loading instead of jq subprocess:
   ```python
   with open(json_file_path, 'r') as f:
       data = json.load(f)
   ```
4. **Query Pattern**: `query_local_markets_rag(local_directory, query)` returns similarity-matched documents

### Market Filtering & Trading Logic
1. **Filter Pipeline** (`filter_markets_for_trading()`):
   - Removes markets where `active=False` or `funded=False` (unless `rewardsMinSize > 0`)
   - Filters out ended markets (`end` date < now)
   - Excludes markets with insufficient liquidity
2. **Sorting Strategy**:
   - Primary: by `spread` (ascending) - lower spread = better liquidity/tighter bid-ask
   - Alternative: by `volume` (descending) for high-activity markets
3. **Autonomous Trading Strategy** (`one_best_trade()`):
   1. Get all tradeable events → 2. Filter events with RAG → 3. Map to markets → 4. Filter markets → 5. Calculate best trade → 6. Execute (if enabled)
4. **Order Types**:
   - Market orders: FOK (Fill-or-Kill) via `execute_market_order()` or `execute_market_order_by_token()`
   - Requires `clob_token_ids` from market object or manual lookup via `find-market-tokens` CLI

### NewsAPI Integration
1. **Query Format**: Comma-separated keywords via `get_articles_for_cli_keywords("keyword1,keyword2")`
2. **Categories**: `business`, `entertainment`, `general`, `health`, `science`, `sports`, `technology`
3. **Returns**: List of `Article` Pydantic objects with `title`, `description`, `url`, `source`, `publishedAt`

### Gamma API Response Parsing
1. **String-to-JSON Fields**: Two fields returned as stringified arrays must be parsed:
   ```python
   market["outcomePrices"] = json.loads(market["outcomePrices"])  # ["0.52", "0.48"]
   market["clobTokenIds"] = json.loads(market["clobTokenIds"])    # ["123", "456"]
   ```
2. **Nested Pydantic Models**: `Market` contains `events: list[PolymarketEvent]`, which contain `tags: list[Tag]`
3. **Pagination**: Use `?limit=X&offset=Y` query params for large result sets

## Code Quality

### Pre-commit Hooks
```bash
pre-commit install  # Required before contributions
# Runs Black (24.4.2) formatter for Python 3.9 compatibility
# Hook config: .pre-commit-config.yaml
```

### Testing
Minimal test coverage exists - `tests/test.py` contains basic unittest examples. No pytest or comprehensive test suite currently implemented. When adding tests:
- Use unittest (already imported in test.py)
- Focus on unit tests for `agents/utils/` and `agents/connectors/`
- Integration tests should mock external APIs (Polymarket, OpenAI, NewsAPI)

### Code Style
- Black formatter with default settings (line length 88)
- Type hints preferred (Pydantic models already enforce this)
- Docstrings: use concise one-liners for CLI commands, detailed docstrings for complex methods in core modules

## Known Gotchas & Common Pitfalls

1. **Terms of Service**: Trading code intentionally disabled by default (`execute=False`). US persons and certain jurisdictions prohibited from trading (see [polymarket.com/tos](https://polymarket.com/tos)). Data/info globally viewable.

2. **PYTHONPATH Requirement**: Must set `PYTHONPATH="."` when running CLI/scripts outside Docker, otherwise imports fail with `ModuleNotFoundError: No module named 'agents'`

3. **API String Formats**: Gamma API returns `outcomePrices` and `clobTokenIds` as stringified JSON arrays - must parse with `json.loads()` before use

4. **Multiple Requirements Files**: Three requirements files exist (`requirements.txt`, `requirements_clean.txt`, `requirements_temp.txt`) - always use `requirements.txt` for installation

5. **Windows PowerShell Syntax**: 
   - Use semicolons `;` to chain commands, **never** `&&`
   - Environment variables: `$env:VAR = "value"` (not `export VAR="value"`)
   - Activation: `.venv\Scripts\Activate.ps1` (not `source .venv/bin/activate`)

6. **Private Key Format**: `POLYGON_WALLET_PRIVATE_KEY` should be raw hex without `0x` prefix. If import fails, check for leading/trailing whitespace.

7. **USDC Confusion**: Two USDC tokens on Polygon:
   - Native USDC (`0x2791...4174`) - **used by Polymarket** ✅
   - Bridged USDC.e (`0x3c49...3359`) - common from Coinbase deposits
   - Must swap USDC.e → native USDC to trade (see root-level helper scripts like `swap_to_native_usdc.py`)

8. **RAG Database Persistence**: Local DBs created with timestamps in filenames (`all-current-markets_{time.time()}.json`). Old files accumulate - manually delete or run `Trader.clear_local_dbs()`.

9. **Gas Requirements**: Need small MATIC balance (~0.01 MATIC) for approvals and trades. Check via `check-matic-balance` CLI command.

10. **Server Port**: FastAPI server defaults to port 8888 (not standard 8000) - override with `--port` if needed

11. **LLM Rate Limits**: OpenAI rate limits can cause failures on bulk operations. Executor chunks data but doesn't implement retry logic - add backoff manually if needed.

12. **Market End Dates**: `end` field is ISO 8601 string. Filter logic compares string dates - ensure proper timezone handling for edge cases.

## Integration Points & External Dependencies

### Core Libraries
- **py-clob-client** (`ClobClient`): Official Polymarket Python CLOB client - handles order placement, market data, API auth
- **py-order-utils** (`OrderBuilder`, `Signer`): EIP-712 structured data signing for order creation
- **web3.py**: Ethereum/Polygon blockchain interaction (balance checks, contract calls, transaction signing)
- **LangChain** (`ChatOpenAI`, `SystemMessage`, `HumanMessage`): LLM orchestration with context management
- **ChromaDB** (`Chroma`, vectorstore): AI-native vector database for RAG embeddings
- **FastAPI** + **Uvicorn**: Web framework for dashboard (async ASGI server)
- **Typer**: CLI framework with decorator-based command registration
- **Pydantic**: Data validation and settings management (all data models inherit `BaseModel`)
- **httpx**: Async HTTP client for external API calls
- **newsapi-python**: NewsAPI wrapper for news sourcing

### External APIs
1. **Polymarket Gamma API** (`https://gamma-api.polymarket.com`):
   - `/markets` - Market metadata (question, outcomes, prices, volumes, clob_token_ids)
   - `/events` - Event metadata (title, description, markets, tags)
   - No auth required, public read-only
2. **Polymarket CLOB API** (`https://clob.polymarket.com`):
   - `/auth/api-key` - Derive API credentials from private key
   - Orderbook operations, trade execution, balance queries
   - Requires EIP-712 signed auth (handled by py-clob-client)
3. **OpenAI API**:
   - GPT models: `gpt-3.5-turbo-16k`, `gpt-4-1106-preview`
   - Embeddings: `text-embedding-3-small`
   - Requires `OPENAI_API_KEY`
4. **NewsAPI** (`https://newsapi.org`):
   - `/v2/top-headlines` - Breaking news by category/country
   - `/v2/everything` - Keyword search across sources
   - Requires `NEWSAPI_API_KEY` (free tier: 100 requests/day)
5. **Tavily API** (optional):
   - Web search for real-time context
   - Requires `TAVILY_API_KEY`
6. **Polygon RPC** (`https://polygon-rpc.com`):
   - Blockchain node for reading contract state, sending transactions
   - No API key required (public endpoint)

### Smart Contracts (Polygon Mainnet)
- **USDC Token** (`0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`): Native USDC used by Polymarket
- **USDC.e Token** (`0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`): Bridged USDC from Ethereum (not used for trading)
- **CTF (Conditional Token Framework)** (`0x4D97DCd97eC945f40cF65F87097ACe5EA0476045`): ERC-1155 contract for outcome tokens
- **CTF Exchange** (`0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E`): Primary DEX for trading
- **Neg Risk Exchange** (`0xC5d563A36AE78145C45a50134d48A1215220f80a`): Alternative exchange for negative risk markets

## Helper Scripts (Root Directory)

The root directory contains utility scripts for wallet management and troubleshooting:

**Wallet Setup & Management:**
- `proper_setup.py`, `auto_setup.py` - Automated wallet/API setup workflows
- `generate_new_wallet.py` - Create new Polygon wallet with private key
- `verify_wallet.py`, `verify_key_match.py` - Verify wallet address matches private key
- `wallet_overview.py` - Display wallet info and balances

**Balance & Transaction Monitoring:**
- `check_balance.py`, `quick_balance.py` - Check USDC/MATIC balances
- `monitor_balance.py` - Continuous balance monitoring
- `check_new_matic.py` - Verify MATIC deposits
- `find_usdc.py` - Locate USDC across wallet addresses

**Token Management:**
- `swap_to_native_usdc.py` - Convert USDC.e → native USDC (required for trading)
- `emergency_transfer.py` - Emergency USDC/token transfer
- `one_click_deposit.py` - Streamlined deposit workflow

**Coinbase Integration:**
- `auto_coinbase.py` - Automated Coinbase deposit/withdrawal
- `test_coinbase.py` - Test Coinbase API connectivity
- `check_coinbase_addresses.py` - Verify Coinbase wallet addresses

**Debugging & Testing:**
- `debug_api.py`, `test_fixed_api.py` - API troubleshooting
- `quick_check.py` - Fast system health check
- `convert_key.py`, `extract_eth_key.py` - Key format conversion utilities
- `check_found_key.py`, `check_old_wallet.py` - Legacy wallet recovery

**Documentation:**
- `HOW_IT_WORKS.md` - Detailed system explanation (CLI trader vs Web UI)
- `SIMPLE_PLAN.py`, `simple_guide.py` - Beginner guides
- `FIXES_COMPLETE.md` - Change log for bug fixes
- `CONTRIBUTING.md` - Contribution guidelines

These scripts are **not** part of the main `agents/` module - they're standalone utilities for initial setup and troubleshooting. Use CLI commands from `scripts/python/cli.py` for standard operations.

## Related Repositories
- [py-clob-client](https://github.com/Polymarket/py-clob-client)
- [python-order-utils](https://github.com/Polymarket/python-order-utils)
- [clob-client](https://github.com/Polymarket/clob-client) (TypeScript)
