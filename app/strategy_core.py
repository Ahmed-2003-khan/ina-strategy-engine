# Purpose: Houses the core business logic for the negotiation strategy.
# (Upgraded to v1.2 - History-Aware "Split the Difference")

from .schemas import StrategyInput, StrategyOutput
import logging
import math

# Set up a logger for this module
logger = logging.getLogger(__name__)

# --- Policy Configuration ---
POLICY_VERSION = "1.3.0"

# Thresholds
LOWBALL_THRESHOLD_PERCENT = 0.70        # Reject if offer is < 70% of MAM
SENTIMENT_ACCEPT_THRESHOLD_PERCENT = 0.95 # Panic accept if offer is >= 95% of MAM & sentiment is negative

def get_last_bot_offer(input_data: StrategyInput) -> float:
    """
    Helper function to find the most recent price offered by the Bot.
    
    It scans the history backwards. 
    - If it finds a bot move with a price, it returns that.
    - If negotiation just started (no history), it returns the original asking_price.
    """
    # Iterate backwards through history to find the latest bot move
    for turn in reversed(input_data.history):
        role = turn.get("role", "").lower()
        if role == "assistant" or role == "bot":
            # Check for common keys where price might be stored
            if "counter_price" in turn and turn["counter_price"] is not None:
                return float(turn["counter_price"])
            if "offer" in turn and turn["offer"] is not None:
                return float(turn["offer"])
                
    # Fallback: If no previous bot offer found, we start at the Asking Price
    return input_data.asking_price

def make_decision(input_data: StrategyInput) -> StrategyOutput:
    """
    Applies the negotiation strategy to decide the next action.
    """
    
    # Log incoming context
    logger.info(f"Processing decision for session: {input_data.session_id}")
    logger.info(f"NLU Data - Sentiment: {input_data.user_sentiment}, Intent: {input_data.user_intent}")

    # =================================================================
    # RULE 1: Sentiment-Based Accept ("The Panic Rule")
    # =================================================================
    sentiment_accept_threshold = input_data.mam * SENTIMENT_ACCEPT_THRESHOLD_PERCENT
    
    if (input_data.user_sentiment == 'negative' and 
        input_data.user_offer >= sentiment_accept_threshold):
        
        logger.warning(f"ACCEPT (Sentiment): Offer {input_data.user_offer} >= threshold {sentiment_accept_threshold}")
        
        return StrategyOutput(
            action="ACCEPT",
            response_key="ACCEPT_SENTIMENT_CLOSE",
            counter_price=input_data.user_offer,
            policy_type="rule-based",
            policy_version=POLICY_VERSION,
            decision_metadata={"rule": "sentiment_accept_on_negative"}
        )

    # =================================================================
    # RULE 2: The Unbreakable Rule (Standard Accept)
    # =================================================================
    if input_data.user_offer >= input_data.mam:
        logger.warning(f"ACCEPT (Standard): Offer {input_data.user_offer} >= MAM {input_data.mam}")
        
        return StrategyOutput(
            action="ACCEPT",
            response_key="ACCEPT_FINAL",
            counter_price=input_data.user_offer,
            policy_type="rule-based",
            policy_version=POLICY_VERSION,
            decision_metadata={"rule": "user_offer_gte_mam"}
        )
    
    # =================================================================
    # RULE 3: Lowball REJECT Logic
    # =================================================================
    lowball_threshold = input_data.mam * LOWBALL_THRESHOLD_PERCENT
    
    if input_data.user_offer < lowball_threshold:
        logger.info(f"REJECT (Lowball): Offer {input_data.user_offer} < threshold {lowball_threshold}")
        
        return StrategyOutput(
            action="REJECT",
            response_key="REJECT_LOWBALL",
            counter_price=None,
            policy_type="rule-based",
            policy_version=POLICY_VERSION,
            decision_metadata={"rule": "user_offer_lt_lowball_threshold"}
        )

    # =================================================================
    # RULE 4: Counter-Offer Logic (History Aware)
    # =================================================================
    # Logic: Meet halfway between the Bot's LAST position and the User's Offer.
    # Constraint: Never go below MAM.
    
    # 1. Determine our current standing
    current_bot_price = get_last_bot_offer(input_data)
    
    # 2. Calculate the "Split the Difference" value
    # Formula: current_position - (current_position - user_offer) * 0.5
    # This calculates the midpoint between where we ARE and where they ARE.
    midpoint = current_bot_price - (current_bot_price - input_data.user_offer) * 0.5
    
    # 3. Apply the Safety Floor using max()
    # If the midpoint is below MAM, we must stop at MAM.
    final_counter = max(input_data.mam, midpoint)
    
    # 4. Round up to nearest whole number
    final_counter = math.ceil(final_counter)
    
    # 5. Sanity Check: Ratchet Effect
    # Ensure we don't accidentally raise our price if the math gets weird
    if final_counter > current_bot_price:
        final_counter = current_bot_price

    logger.info(f"COUNTER: Last Bot Price {current_bot_price} -> User {input_data.user_offer} -> Final {final_counter}")

    return StrategyOutput(
        action="COUNTER",
        response_key="STANDARD_COUNTER",
        counter_price=final_counter,
        policy_type="rule-based",
        policy_version=POLICY_VERSION,
        decision_metadata={
            "rule": "split_difference_max_mam",
            "mam": input_data.mam,
            "last_bot_price": current_bot_price,
            "user_offer": input_data.user_offer,
            "final_counter": final_counter
        }
    )