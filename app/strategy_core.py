# Purpose: Houses the core business logic for the negotiation strategy.
# This is deliberately decoupled from the FastAPI web framework.

from .schemas import StrategyInput, StrategyOutput
import logging

# Set up a logger for this module
logger = logging.getLogger(__name__)

def make_decision(input_data: StrategyInput) -> StrategyOutput:
    """
    Applies the negotiation strategy to decide the next action.
    
    This is the "pluggable" component. We can swap this function
    with an RL policy loader in the future.
    """
    
    logger.info(f"Processing decision for session: {input_data.session_id}")
    
    # --- The Unbreakable Rule (Today's Task) ---
    # This is the primary security and business rule.
    # If the user's offer meets our minimum, we accept.
    if input_data.user_offer >= input_data.mam:
        logger.warning(f"ACCEPT: User offer ({input_data.user_offer}) >= MAM.")
        
        return StrategyOutput(
            action="ACCEPT",
            response_key="ACCEPT_FINAL",
            counter_price=input_data.user_offer, # Confirming the accepted price
            policy_type="rule-based",
            policy_version="1.0.0",
            decision_metadata={"rule": "user_offer_gte_mam"}
        )
    
    # --- Placeholder for Tomorrow's Logic ---
    # If the rule above doesn't trigger, we fall through.
    # For today, we'll return a basic "REJECT" as a placeholder.
    # On Thursday, you will replace this block with the
    # REJECT (lowball) and COUNTER logic.
    else:
        logger.info(f"Offer ({input_data.user_offer}) is below MAM. Pending negotiation.")
        
        # This is a temporary response.
        # Tomorrow, this 'else' block will contain the
        # Lowball REJECT vs. standard COUNTER logic.
        return StrategyOutput(
            action="REJECT", # Placeholder action
            response_key="TEMP_REJECT", # Placeholder key
            policy_type="rule-based",
            policy_version="1.0.0",
            decision_metadata={"rule": "temp_offer_lt_mam"}
        )