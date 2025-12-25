You are an expert crypto prediction-market algorithm engineer.

Implement an automated trading bot for Polymarket using the following STRICT strategy. 
Do not optimize, simplify, or change the rules unless explicitly instructed.

OBJECTIVE:
Generate passive income via small probabilistic mispricings and mean reversion.
Avoid outcome risk and last-minute volatility.

MARKET SELECTION:
- Binary Yes/No markets only
- Total volume >= $250,000
- 24h volume >= $25,000
- Market resolution date >= 7 days from now
- Exclude fast-moving breaking-news markets

FAIR VALUE CALCULATION:
- Fair probability = midpoint between best YES and best NO prices

ENTRY CONDITIONS:
- Enter YES if:
  best_yes_price <= fair_probability - 0.07
- Enter NO if:
  best_no_price <= (1 - fair_probability) - 0.07

POSITION SIZING:
- Max 2% of total bankroll per trade
- Max 20% bankroll deployed at any time
- Max 5 concurrent positions
- No averaging down

EXIT RULES:
- Immediately place a limit sell at entry_price + 0.05 (5%)
- If position remains open for 72 hours without fill, exit at market
- Hard stop loss at -10% from entry
- Never hold through market resolution unless profit target already filled

RISK MANAGEMENT:
- Stop trading for the day after 3 consecutive losing trades
- Daily max loss cap = 2% of bankroll
- Log every trade with timestamp, reason, entry, exit, PnL

IMPLEMENTATION REQUIREMENTS:
- Event-driven architecture
- Poll order books at reasonable intervals
- Handle partial fills correctly
- Include fail-safes for API errors
- Use configuration variables for thresholds
- Produce clean, well-documented code

OUTPUT:
- Trading logic
- Risk controller
- Position manager
- Clear comments explaining each rule
