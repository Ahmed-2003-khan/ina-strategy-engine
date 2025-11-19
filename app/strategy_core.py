# Purpose: Houses the core business logic for the negotiation strategy.
# (Upgraded to v1.1 - Sentiment-Aware)

from .schemas import StrategyInput, StrategyOutput
import logging
import math

# Set up a logger for this module
logger = logging.getLogger(__name__)

# --- Policy Configuration ---
# We've updated the logic, so we version bump
POLICY_VERSION = "1.2.0"  # v1.1 was schema, v1.2 is this logic
LOWBALL_THRESHOLD_PERCENT = 0.70 # 70% of MAM
SENTIMENT_ACCEPT_THRESHOLD_PERCENT = 0.95 # 95% of MAM
# --- NEW: Counter-offer "jump" percentage ---
# 0.75 means we will counter 75% of the way from the user's offer to our MAM
COUNTER_JUMP_WEIGHT = 0.75

def make_decision(input_data: StrategyInput) -> StrategyOutput:
    """
    Applies the negotiation strategy (v1.2) to decide the next action.
    Now includes sentiment-based "panic" rule.
    """
    
    logger.info(f"Processing decision for session: {input_data.session_id}")
    logger.info(f"Received sentiment: {input_data.user_sentiment}, intent: {input_data.user_intent}")

    # --- NEW: Rule 1 (High Priority): Sentiment-Based Accept ---
    # Logic: if input.user_offer >= (input.mam * 0.95) and input.sentiment == 'negative'
    # This rule saves a sale if the user is frustrated and their offer is "close enough".
    
    sentiment_accept_threshold = input_data.mam * SENTIMENT_ACCEPT_THRESHOLD_PERCENT
    
    if (input_data.user_sentiment == 'negative' and 
        input_data.user_offer >= sentiment_accept_threshold):
        
        logger.warning(
            f"ACCEPT (Sentiment Rule): User offer ({input_data.user_offer}) "
            f">= panic threshold ({sentiment_accept_threshold}) "
            f"and sentiment is '{input_data.user_sentiment}'."
        )
        
        return StrategyOutput(
            action="ACCEPT",
            response_key="ACCEPT_SENTIMENT_CLOSE", # A new key for MS 5
            counter_price=input_data.user_offer,
            policy_type="rule-based",
            policy_version=POLICY_VERSION,
            decision_metadata={
                "rule": "sentiment_accept_on_negative",
                "mam": input_data.mam,
                "user_offer": input_data.user_offer,
                "sentiment": input_data.user_sentiment,
                "threshold_percent": SENTIMENT_ACCEPT_THRESHOLD_PERCENT,
                "threshold_value": sentiment_accept_threshold
            }
        )

    # --- Rule 2: The Unbreakable Rule (Standard Accept) ---
    # This rule only runs if the sentiment rule *fails*.
    if input_data.user_offer >= input_data.mam:
        logger.warning(f"ACCEPT (Standard): User offer ({input_data.user_offer}) >= MAM.")
        
        return StrategyOutput(
            action="ACCEPT",
            response_key="ACCEPT_FINAL",
            counter_price=input_data.user_offer,
            policy_type="rule-based",
            policy_version=POLICY_VERSION,
            decision_metadata={
                "rule": "user_offer_gte_mam",
                "mam": input_data.mam,
                "user_offer": input_data.user_offer
            }
        )
    
    # --- Rule 3: Lowball REJECT Logic ---
    # Logic: if input.user_offer < (input.mam * 0.7)
    
    lowball_threshold = input_data.mam * LOWBALL_THRESHOLD_PERCENT
    
    if input_data.user_offer < lowball_threshold:
        logger.info(f"REJECT (LOWBALL): User offer ({input_data.user_offer}) < threshold ({lowball_threshold}).")
        
        return StrategyOutput(
            action="REJECT",
            response_key="REJECT_LOWBALL",
            counter_price=None,
            policy_type="rule-based",
            policy_version=POLICY_VERSION,
            decision_metadata={
                "rule": "user_offer_lt_lowball_threshold",
                "mam": input_data.mam,
                "user_offer": input_data.user_offer,
                "threshold_percent": LOWBALL_THRESHOLD_PERCENT,
                "threshold_value": lowball_threshold
            }
        )

    # --- Rule 4: Smarter COUNTER-OFFER Logic (Today's Task) ---
    
    # OLD LOGIC (for reference):
    # counter_offer = math.ceil((input_data.asking_price + input_data.user_offer) / 2)
    
    # NEW "WEIGHTED JUMP" LOGIC:
    # We calculate the remaining "gap" to our MAM
    gap_to_mam = input_data.mam - input_data.user_offer
    
    # We decide to "jump" 75% of that gap
    jump_amount = gap_to_mam * COUNTER_JUMP_WEIGHT
    
    # Our new counter is the user's offer + our jump
    # We use ceil() to round up, making the counter slightly tougher
    counter_offer = math.ceil(input_data.user_offer + jump_amount)
    
    # --- CRITICAL: Counter-offer Sanity Check (No Change) ---
    # This logic MUST remain. We must ensure our new formula
    # *never* accidentally calculates a counter *below* the MAM.
    # (In this case, it should always be >= MAM, but this check is our seatbelt).
    if counter_offer < input_data.mam:
        logger.warning(f"Counter ({counter_offer}) was < MAM. Adjusting to MAM.")
        counter_offer = input_data.mam 
        
    # --- NEW: Secondary Sanity Check ---
    # We also must ensure our counter is not *higher* than the asking price.
    if counter_offer > input_data.asking_price:
        logger.warning(f"Counter ({counter_offer}) > asking price. Clamping to {input_data.asking_price}.")
        counter_offer = input_data.asking_price
        
    logger.info(f"COUNTER: User offer ({input_data.user_offer}). Weighted-jump counter: {counter_offer}.")

    return StrategyOutput(
        action="COUNTER",
        response_key="STANDARD_COUNTER",
        counter_price=counter_offer,
        policy_type="rule-based",
        policy_version=POLICY_VERSION,
        decision_metadata={
            "rule": "weighted_jump_counter",
            "mam": input_data.mam,
            "user_offer": input_data.user_offer,
            "jump_weight": COUNTER_JUMP_WEIGHT,
            "calculated_counter": counter_offer
        }
    )