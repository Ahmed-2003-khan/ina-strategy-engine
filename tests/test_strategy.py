# Purpose: Unit tests for the core negotiation logic.
# These tests ensure that the 'make_decision' function behaves
# exactly as expected under all conditions.

import pytest
import logging 
from app.strategy_core import make_decision
from app.schemas import StrategyInput

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =======================================================================
#  Test Data Fixtures
# =======================================================================

# A 'base' input that we can modify for each test case.
# This makes tests cleaner as we only change what's relevant.
@pytest.fixture
def base_input():
    """A standard baseline input for negotiation."""
    return StrategyInput(
        mam=42000.0,
        asking_price=50000.0,
        user_offer=45000.0,  # Note: this default will trigger ACCEPT
        session_id="sess_test_fixture",
        history=[]
    )

# =======================================================================
#  Test Cases for make_decision()
# =======================================================================

def test_unbreakable_rule_accept_offer_above_mam(base_input):
    """
    Test Rule 1: ACCEPT
    If user_offer is greater than mam, we MUST accept.
    """
    # Arrange
    base_input.user_offer = 43000.0
    base_input.mam = 42000.0
    
    # Act
    decision = make_decision(base_input)
    
    # Assert
    assert decision.action == "ACCEPT"
    assert decision.response_key == "ACCEPT_FINAL"
    assert decision.counter_price == 43000.0 # Confirms the accepted price
    assert decision.decision_metadata["rule"] == "user_offer_gte_mam"

def test_unbreakable_rule_accept_offer_equals_mam(base_input):
    """
    Test Edge Case for Rule 1: ACCEPT
    If user_offer is exactly equal to mam, we MUST accept.
    """
    # Arrange
    base_input.user_offer = 42000.0
    base_input.mam = 42000.0
    
    # Act
    decision = make_decision(base_input)
    
    # Assert
    assert decision.action == "ACCEPT"
    assert decision.response_key == "ACCEPT_FINAL"
    assert decision.counter_price == 42000.0

def test_lowball_reject(base_input):
    """
    Test Rule 2: REJECT (Lowball)
    If user_offer is < 70% of mam.
    """
    # Arrange
    base_input.mam = 42000.0
    base_input.user_offer = 25000.0 # This is < (42000 * 0.7 = 29400)
    
    # Act
    decision = make_decision(base_input)
    
    # Assert
    assert decision.action == "REJECT"
    assert decision.response_key == "REJECT_LOWBALL"
    assert decision.counter_price is None # Must not counter on a lowball
    assert decision.decision_metadata["rule"] == "user_offer_lt_lowball_threshold"

def test_lowball_reject_edge_case(base_input):
    """
    Test Edge Case for Rule 2: REJECT (Lowball)
    What if the offer is *just* below the threshold?
    """
    # Arrange
    base_input.mam = 42000.0
    # Threshold is 29400. Let's offer 29399.99
    base_input.user_offer = 29399.99
    
    # Act
    decision = make_decision(base_input)
    
    # Assert
    assert decision.action == "REJECT"
    assert decision.response_key == "REJECT_LOWBALL"

def test_standard_counter(base_input):
    """
    Test Rule 3: COUNTER
    Offer is > lowball threshold but < mam.
    """
    # Arrange
    base_input.mam = 42000.0
    base_input.asking_price = 50000.0
    base_input.user_offer = 40000.0 # > 29400 (lowball) and < 42000 (mam)
    
    # Act
    decision = make_decision(base_input)
    
    # Assert
    assert decision.action == "COUNTER"
    assert decision.response_key == "STANDARD_COUNTER"
    # Mid-point: ceil((50000 + 40000) / 2) = 45000
    assert decision.counter_price == 45000.0 
    assert decision.decision_metadata["rule"] == "standard_counter_midpoint"

def test_standard_counter_edge_case_at_threshold(base_input, caplog):
    """
    Test Edge Case for Rule 3: COUNTER
    What if the offer is *exactly* the lowball threshold?
    It should be treated as a COUNTER, not a REJECT.
    """
    # Arrange
    base_input.mam = 42000.0
    base_input.asking_price = 50000.0
    base_input.user_offer = 29400.0 # Exactly 70% of MAM
    
    # Act
    decision = make_decision(base_input)
    
    # Assert
    assert decision.action == "COUNTER"
    # Mid-point: ceil((50000 + 29400) / 2) = 39700
    # Sanity Check: 39700 is less than MAM (42000).
    # The logic should clamp this counter *up* to MAM.
    assert decision.counter_price == 42000.0
    assert decision.decision_metadata["rule"] == "standard_counter_midpoint"
    assert "Counter (39700.0) was < MAM" in caplog.text # Check the log!

# This is a more advanced test using parametrize and caplog
@pytest.mark.parametrize("user_offer, asking_price, expected_counter", [
    (40000, 50000, 45000), # Standard case: (40k+50k)/2 = 45k
    (30000, 50000, 42000), # Mid-point (40k) < MAM (42k), so clamp to 42k
    (41000, 43000, 42000), # Mid-point (42k) == MAM, OK
    (41000, 44000, 42500), # Mid-point (42.5k) > MAM, OK
])
def test_counter_offer_sanity_check_logic(base_input, caplog, user_offer, asking_price, expected_counter):
    """
    Test Rule 3's "Sanity Check" with multiple values.
    Ensures our counter-offer is never below MAM.
    """
    # Arrange
    base_input.mam = 42000.0
    base_input.user_offer = user_offer
    base_input.asking_price = asking_price
    
    # Act
    # We capture logs to see if our warning message was printed
    with caplog.at_level(logging.WARNING):
        decision = make_decision(base_input)
    
    # Assert
    assert decision.action == "COUNTER"
    assert decision.counter_price == expected_counter
    
    # If we expected a clamp, check that the warning log was created
    if expected_counter == base_input.mam and user_offer != 41000:
         assert "was < MAM. Adjusting to MAM." in caplog.text