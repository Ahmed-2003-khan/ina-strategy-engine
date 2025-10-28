# Purpose: Defines the data contracts (schemas) for your API.
# Pydantic validates all incoming data against these models.

from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Any, Optional

# =======================================================================
#  API Input Schema
# =======================================================================

class StrategyInput(BaseModel):
    """
    The data payload sent FROM the Dialogue Orchestrator (MS 1)
    TO this service (MS 4: The Brain).
    """
    
    # Core Financial Data (THE SECRET)
    # This data MUST NOT be passed to MS 5 (The Mouth).
    mam: float = Field(
        ...,
        description="Minimum Acceptable Margin. The secret financial floor."
    )
    
    # Contextual Negotiation Data
    asking_price: float = Field(
        ..., 
        description="The initial price listed or offered by the business."
    )
    user_offer: float = Field(
        ..., 
        description="The latest price offered by the user."
    )
    
    # Dialogue & State
    session_id: str = Field(
        ..., 
        description="Unique identifier for the negotiation session."
    )
    history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Log of conversation turns (e.g., [{'role': 'user', 'offer': 45000}, ...])"
    )

    class Config:
        # Example for documentation
        json_schema_extra = {
            "example": {
                "mam": 42000.0,
                "asking_price": 50000.0,
                "user_offer": 45000.0,
                "session_id": "sess_12345abc",
                "history": [
                    {"role": "bot", "action": "GREET"},
                    {"role": "user", "offer": 45000.0}
                ]
            }
        }

# =======================================================================
#  API Output Schema
# =======================================================================

class StrategyOutput(BaseModel):
    """
    The data payload (a 'command') sent FROM this service (MS 4)
    TO the Dialogue Orchestrator (MS 1), which then forwards it
    to MS 5 (The Mouth).
    
    This payload MUST NOT contain the 'mam' or any secret financial data.
    """
    
    # The decision made by the strategy engine
    action: Literal["ACCEPT", "REJECT", "COUNTER"] = Field(
        ..., 
        description="The negotiation action to take."
    )
    
    # The key for MS 5 (LLM) to use for phrasing the response
    response_key: str = Field(
        ..., 
        description="A structured key for MS 5 to select the right response template."
        # e.g., "GREET", "ACCEPT_FINAL", "REJECT_LOWBALL", "COUNTER_STANDARD"
    )
    
    # Optional field, only present if action is 'COUNTER'
    counter_price: Optional[float] = Field(
        default=None, 
        description="The new price to offer (if action is COUNTER)."
    )
    
    # --- Hooks for Future RL Integration ---
    
    policy_type: str = Field(
        default="rule-based",
        description="The type of policy that made this decision (e.g., 'rule-based', 'rl-ppo-v2')."
    )
    
    policy_version: Optional[str] = Field(
        default="1.0.0",
        description="The version of the policy used, for A/B testing and logging."
    )
    
    decision_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional data for audit/logging (e.g., confidence score, features used)."
    )

    class Config:
        # Example for documentation
        json_schema_extra = {
            "example": {
                "action": "COUNTER",
                "response_key": "STANDARD_COUNTER",
                "counter_price": 48000.0,
                "policy_type": "rule-based",
                "policy_version": "1.0.0",
                "decision_metadata": {"reason": "User offer > 70% of MAM, applying mid-point formula."}
            }
        }