

**Prompt for VS Code Agent:**

You are an expert Python developer fixing a Polymarket trading bot that is currently generating dangerous, overconfident recommendations, especially on sports markets.

The latest run (December 2025) showed catastrophic model miscalibration on Super Bowl 2026 winner markets:
- Jacksonville Jaguars: Model 95% vs Market ~6% → recommending massive edge
- Los Angeles Rams: Model 75% vs Market ~16%
- San Francisco 49ers: Model 50% vs Market ~7-14%
These are clearly wrong — no credible analysis gives the Jaguars 95% chance to win the Super Bowl.

Your task: Fix the forecasting and recommendation logic to prevent these kinds of bad trades. The bot must become conservative, calibrated, and safe for manual execution on polymarket.com.

Implement the following fixes in priority order:

1. **Add Hard Sanity Caps Based on Market Volume and Category**
   - For any market with total volume > $100,000:
     - Maximum allowed model probability deviation from market price: 20%
     - Example: If market prices Yes at 10%, model cannot output >30% or <0%
   - For Super Bowl or major championship winner markets (detect via keywords like "Super Bowl", "World Cup", "Championship", "win the"):
     - Cap model probability at market_price + 10% max
     - Never allow model prob > 50% on any single team unless market already >40%
   - For any outcome priced <5¢ or >95¢, require model within 5% of market or skip

2. **Add Explicit Sports Market Handling**
   - Detect sports markets by keywords in question: "win Super Bowl", "win the", "champion", "MVP", "player prop", team names + "vs"
   - For detected sports markets:
     - Use a conservative model: model_prob = market_price * 1.1 + (1 - market_price) * 0.05  (slight fade of extremes)
     - Or simply set edge threshold to 15% minimum (effectively skipping most sports unless huge mispricing)
     - Log: "Sports market detected — applying conservative override"

3. **Improve Edge Validation**
   - Current edge calculation is too permissive. Add:
     ```python
     if abs(model_prob - market_prob) < 0.05:  # 5%
         skip — "Insufficient edge"
     if market_volume > 500_000 and abs(model_prob - market_prob) > 0.30:
         skip — "Implausible deviation in high-volume market"
     ```
   - Require minimum volume-weighted confidence: bigger markets need bigger edges

4. **Prioritize Non-Sports Categories**
   - Boost politics, economics, crypto, geopolitics
   - Example: tariff revenue markets in the latest run (12-17% edges) are realistic — keep and promote those
   - Demote or skip pure sports unless volume < $100k (niche = possible edge)

5. **Output Improvements**
   - In recommendations, add a "Confidence" flag: High/Medium/Low based on volume and edge realism
   - For any recommended trade, include:
     - "Warning: Sports market — higher risk of miscalibration" if applicable
     - Direct Polymarket link (construct from slug or question)
   - In daily summary, separate "Recommended (Non-Sports)" and "Sports (Review Manually)"

6. **Temporary Hotfix for Immediate Safety**
   - Until better model is built, add this rule:
     ```python
     if "super bowl" in question.lower() and edge > 20%:
         action = "NO_TRADE"
         reason = "Sports miscalibration guardrail triggered"
     ```

Focus changes in edge_model.py and filters.py. Make rules modular and clearly commented.

After these fixes, the bot should:
- Recommend the realistic tariff revenue bets
- Skip or heavily downgrade the absurd Super Bowl bets
- Become safe for manual trading on polymarket.com

Implement step by step, starting with the sports detection and hard caps.

---

Paste this prompt directly into your agent. After it applies the changes, run the bot again with `--relaxed` or `--eoy`. You should see clean, believable recommendations focused on politics/economics/crypto, with sports either skipped or flagged as low-confidence.
