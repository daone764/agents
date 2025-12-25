"""
Dual AI Forecaster - Ensemble predictions from GPT-4o-mini + Grok
Uses both AIs and averages predictions when they agree, flags disagreements.
"""
import os
import logging
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from openai import OpenAI

logger = logging.getLogger(__name__)

load_dotenv()


@dataclass
class ForecastResult:
    """Result from dual AI forecasting"""
    probability: float  # Combined probability (0-1)
    outcome: str  # "Yes" or "No"
    confidence: str  # "high", "medium", "low"
    gpt_prob: Optional[float]  # GPT-4o-mini probability
    grok_prob: Optional[float]  # Grok probability
    agreement: float  # How close the predictions are (0-1, 1=perfect agreement)
    reasoning: str  # Combined reasoning
    should_skip: bool  # True if AIs disagree too much


class DualForecaster:
    """
    Ensemble forecaster using GPT-4o-mini and Grok.
    
    Strategy:
    - Get probability from both AIs
    - If they agree (within threshold): Average and proceed with high confidence
    - If they disagree: Flag for manual review, lower confidence
    """
    
    # Agreement thresholds
    HIGH_AGREEMENT_THRESHOLD = 0.10  # Within 10% = high confidence
    SKIP_THRESHOLD = 0.20  # More than 20% apart = skip trade
    
    def __init__(self):
        """Initialize both AI clients"""
        # GPT-4o-mini via LangChain
        self.gpt_model = "gpt-4o-mini"
        self.gpt_client = ChatOpenAI(
            model=self.gpt_model,
            temperature=0,
        )
        
        # Grok via OpenAI-compatible API
        self.xai_api_key = os.getenv("XAI_API_KEY")
        self.grok_client = None
        self.grok_model = "grok-3"  # Latest Grok model
        
        if self.xai_api_key:
            self.grok_client = OpenAI(
                api_key=self.xai_api_key,
                base_url="https://api.x.ai/v1"
            )
            logger.info(f"✓ Dual AI enabled: {self.gpt_model} + {self.grok_model}")
        else:
            logger.warning("⚠️ XAI_API_KEY not set - using GPT-4o-mini only")
    
    def forecast(
        self,
        question: str,
        description: str,
        outcomes: list,
        context: str,
        prompt_template: str
    ) -> ForecastResult:
        """
        Get ensemble forecast from both AIs.
        
        Args:
            question: Market question
            description: Market description
            outcomes: List of possible outcomes
            context: Real-time context (news, search results)
            prompt_template: The forecasting prompt
        
        Returns:
            ForecastResult with combined prediction
        """
        # Get GPT forecast
        gpt_prob, gpt_outcome, gpt_reasoning = self._get_gpt_forecast(prompt_template)
        
        # Get Grok forecast (if available)
        grok_prob, grok_outcome, grok_reasoning = None, None, None
        if self.grok_client:
            grok_prob, grok_outcome, grok_reasoning = self._get_grok_forecast(
                question, description, outcomes, context
            )
        
        # Combine results
        return self._combine_forecasts(
            gpt_prob, gpt_outcome, gpt_reasoning,
            grok_prob, grok_outcome, grok_reasoning,
            question
        )
    
    def _get_gpt_forecast(self, prompt: str) -> Tuple[Optional[float], Optional[str], str]:
        """Get forecast from GPT-4o-mini"""
        try:
            result = self.gpt_client.invoke(prompt)
            response = result.content
            
            prob, outcome = self._parse_probability(response)
            logger.info(f"GPT-4o-mini: {prob*100:.1f}% {outcome}" if prob else "GPT-4o-mini: Failed to parse")
            
            return prob, outcome, response[:500]
            
        except Exception as e:
            logger.error(f"GPT forecast failed: {e}")
            return None, None, str(e)
    
    def _get_grok_forecast(
        self,
        question: str,
        description: str,
        outcomes: list,
        context: str
    ) -> Tuple[Optional[float], Optional[str], str]:
        """Get forecast from Grok"""
        try:
            # Grok-specific prompt (more conversational)
            prompt = f"""You are a superforecaster analyzing prediction markets.

QUESTION: {question}

DESCRIPTION: {description}

POSSIBLE OUTCOMES: {', '.join(outcomes) if outcomes else 'Yes / No'}

REAL-TIME CONTEXT:
{context[:2000]}

Analyze this market and provide your probability estimate.

IMPORTANT: End your response with EXACTLY this format:
PROBABILITY: [number between 0 and 100]%
OUTCOME: [Yes or No]

Example: "PROBABILITY: 65%\nOUTCOME: Yes"

Now provide your analysis:"""
            
            response = self.grok_client.chat.completions.create(
                model=self.grok_model,
                messages=[
                    {"role": "system", "content": "You are an expert forecaster who provides precise probability estimates. Always end with PROBABILITY: X% and OUTCOME: Yes/No."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=1000
            )
            
            response_text = response.choices[0].message.content
            prob, outcome = self._parse_probability(response_text)
            
            logger.info(f"Grok: {prob*100:.1f}% {outcome}" if prob else "Grok: Failed to parse")
            
            return prob, outcome, response_text[:500]
            
        except Exception as e:
            logger.error(f"Grok forecast failed: {e}")
            return None, None, str(e)
    
    def _parse_probability(self, response: str) -> Tuple[Optional[float], Optional[str]]:
        """Parse probability and outcome from AI response"""
        import re
        
        prob = None
        outcome = "Yes"
        
        # Try to find PROBABILITY: X% pattern
        prob_match = re.search(r'PROBABILITY[:\s]+(\d+(?:\.\d+)?)\s*%', response, re.IGNORECASE)
        if prob_match:
            prob = float(prob_match.group(1)) / 100.0
        else:
            # Fallback: look for any percentage
            pct_matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', response)
            if pct_matches:
                # Take the last percentage mentioned (usually the conclusion)
                prob = float(pct_matches[-1]) / 100.0
        
        # Find outcome
        outcome_match = re.search(r'OUTCOME[:\s]+(Yes|No)', response, re.IGNORECASE)
        if outcome_match:
            outcome = outcome_match.group(1).capitalize()
        
        # Clamp probability
        if prob is not None:
            prob = max(0.01, min(0.99, prob))
        
        return prob, outcome
    
    def _combine_forecasts(
        self,
        gpt_prob: Optional[float],
        gpt_outcome: Optional[str],
        gpt_reasoning: str,
        grok_prob: Optional[float],
        grok_outcome: Optional[str],
        grok_reasoning: str,
        question: str
    ) -> ForecastResult:
        """Combine forecasts from both AIs"""
        
        # If only GPT available
        if gpt_prob is None and grok_prob is None:
            return ForecastResult(
                probability=0.5,
                outcome="Yes",
                confidence="low",
                gpt_prob=None,
                grok_prob=None,
                agreement=0,
                reasoning="Both AI forecasts failed",
                should_skip=True
            )
        
        if grok_prob is None:
            # Only GPT available
            return ForecastResult(
                probability=gpt_prob,
                outcome=gpt_outcome or "Yes",
                confidence="medium",
                gpt_prob=gpt_prob,
                grok_prob=None,
                agreement=1.0,
                reasoning=f"GPT-4o-mini only: {gpt_reasoning[:200]}",
                should_skip=False
            )
        
        if gpt_prob is None:
            # Only Grok available
            return ForecastResult(
                probability=grok_prob,
                outcome=grok_outcome or "Yes",
                confidence="medium",
                gpt_prob=None,
                grok_prob=grok_prob,
                agreement=1.0,
                reasoning=f"Grok only: {grok_reasoning[:200]}",
                should_skip=False
            )
        
        # Both available - calculate agreement
        disagreement = abs(gpt_prob - grok_prob)
        agreement = 1.0 - disagreement
        
        # Average the probabilities
        avg_prob = (gpt_prob + grok_prob) / 2.0
        
        # Determine confidence based on agreement
        if disagreement <= self.HIGH_AGREEMENT_THRESHOLD:
            confidence = "high"
            should_skip = False
        elif disagreement <= self.SKIP_THRESHOLD:
            confidence = "medium"
            should_skip = False
        else:
            confidence = "low"
            should_skip = True  # AIs disagree too much
        
        # Determine outcome (go with majority or GPT if tied)
        if gpt_outcome == grok_outcome:
            outcome = gpt_outcome
        else:
            # Use the one with more extreme probability
            outcome = gpt_outcome if abs(gpt_prob - 0.5) > abs(grok_prob - 0.5) else grok_outcome
        
        reasoning = f"GPT-4o-mini: {gpt_prob*100:.0f}% | Grok: {grok_prob*100:.0f}% | Agreement: {agreement*100:.0f}%"
        
        if should_skip:
            reasoning += f" ⚠️ SKIP: AIs disagree by {disagreement*100:.0f}%"
            logger.warning(f"⚠️ AI DISAGREEMENT on '{question[:50]}...': GPT={gpt_prob*100:.0f}%, Grok={grok_prob*100:.0f}%")
        else:
            logger.info(f"✓ AI AGREEMENT: GPT={gpt_prob*100:.0f}%, Grok={grok_prob*100:.0f}%, Avg={avg_prob*100:.0f}%")
        
        return ForecastResult(
            probability=avg_prob,
            outcome=outcome or "Yes",
            confidence=confidence,
            gpt_prob=gpt_prob,
            grok_prob=grok_prob,
            agreement=agreement,
            reasoning=reasoning,
            should_skip=should_skip
        )


# Simple test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    forecaster = DualForecaster()
    
    # Test question
    test_prompt = """You are a superforecaster.
    
QUESTION: Will Bitcoin exceed $100,000 by end of 2025?

Provide your probability estimate.
End with: PROBABILITY: X% and OUTCOME: Yes/No"""
    
    result = forecaster.forecast(
        question="Will Bitcoin exceed $100,000 by end of 2025?",
        description="Resolves YES if BTC/USD exceeds $100,000 at any point before Dec 31, 2025",
        outcomes=["Yes", "No"],
        context="Bitcoin currently trading around $98,000. Recent ETF inflows strong.",
        prompt_template=test_prompt
    )
    
    print(f"\n{'='*60}")
    print(f"DUAL AI FORECAST RESULT")
    print(f"{'='*60}")
    print(f"Combined Probability: {result.probability*100:.1f}%")
    print(f"Outcome: {result.outcome}")
    print(f"Confidence: {result.confidence}")
    print(f"GPT-4o-mini: {result.gpt_prob*100:.1f}%" if result.gpt_prob else "GPT: N/A")
    print(f"Grok: {result.grok_prob*100:.1f}%" if result.grok_prob else "Grok: N/A")
    print(f"Agreement: {result.agreement*100:.0f}%")
    print(f"Should Skip: {result.should_skip}")
    print(f"Reasoning: {result.reasoning}")
