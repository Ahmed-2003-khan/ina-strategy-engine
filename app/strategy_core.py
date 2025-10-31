# Purpose: Houses the core business logic for the negotiation strategy.
# This is deliberately decoupled from the FastAPI web framework.

from .schemas import StrategyInput, StrategyOutput
import logging
import math

# Set up a logger for this module
logger = logging.getLogger(__name__)

# --- Policy Configuration ---
# By defining rules as constants, we can easily change them later
# or even load them from an external config file or service.
POLICY_VERSION = "1.1.0"  # We've updated the logic, so we version bump
LOWBALL_THRESHOLD_PERCENT = 0.70 # 70% of MAM

def make_decision(input_data: StrategyInput) -> StrategyOutput:
    """
    Applies the negotiation strategy to decide the next action.
    
    This is the "pluggable" component. We can swap this function
    with an RL policy loader in the future.
    """
    
    logger.info(f"Processing decision for session: {input_data.session_id}")
    
    # --- Rule 1: The Unbreakable Rule (from Wednesday) ---
    if input_data.user_offer >= input_data.mam:
        logger.warning(f"ACCEPT: User offer ({input_data.user_offer}) >= MAM.")
        
        return StrategyOutput(
            action="ACCEPT",
            response_key="ACCEPT_FINAL",
            counter_price=input_data.user_offer, # Confirming the accepted price
            policy_type="rule-based",
            policy_version=POLICY_VERSION,
            decision_metadata={
                "rule": "user_offer_gte_mam",
                "mam": input_data.mam,
                "user_offer": input_data.user_offer
            }
        )
    
    # --- Rule 2: Lowball REJECT Logic (Today's Task) ---
    # Logic: if input.user_offer < (input.mam * 0.7)
    
    lowball_threshold = input_data.mam * LOWBALL_THRESHOLD_PERCENT
    
    if input_data.user_offer < lowball_threshold:
        logger.info(f"REJECT (LOWBALL): User offer ({input_data.user_offer}) < threshold ({lowball_threshold}).")
        
        return StrategyOutput(
            action="REJECT",
            response_key="REJECT_LOWBALL",
            counter_price=None, # No counter on a lowball
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

    # --- Rule 3: Standard COUNTER-OFFER Logic (Today's Task) ---
    # Logic: This is the 'else' case. The offer is < MAM, but > lowball threshold.
    # We will counter with the mid-point between their offer and the asking price.
    
    # Calculate the counter offer: (asking_price + user_offer) / 2
    # We use math.ceil to round up to be slightly tougher in negotiation.
    counter_offer = float(math.ceil((input_data.asking_price + input_data.user_offer) / 2))
    
    # --- Counter-offer Sanity Check ---
    # A crucial check: Our counter-offer should NEVER be lower than our MAM.
    # If the mid-point formula results in a value < MAM, we should counter
    # with MAM (or slightly above it) instead.
    if counter_offer < input_data.mam:
        logger.warning(f"Counter ({counter_offer}) was < MAM. Adjusting to MAM.")
        counter_offer = input_data.mam 
        
    logger.info(f"COUNTER: User offer ({input_data.user_offer}). Countering with {counter_offer}.")

    return StrategyOutput(
        action="COUNTER",
        response_key="STANDARD_COUNTER",
        counter_price=counter_offer,
        policy_type="rule-based",
        policy_version=POLICY_VERSION,
        decision_metadata={
            "rule": "standard_counter_midpoint",
            "mam": input_data.mam,
            "user_offer": input_data.user_offer,
            "asking_price": input_data.asking_price,
            "calculated_counter": counter_offer
        }
    )