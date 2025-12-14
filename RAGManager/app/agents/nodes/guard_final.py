"""Nodo Guard Final - Validates generated response for PII (Personally Identifiable Information)."""

import logging

from guardrails import Guard
from guardrails.hub import DetectPII

from app.agents.state import AgentState

logger = logging.getLogger(__name__)

# Initialize Guard with DetectPII validator
# Note: The validator must be installed via: guardrails hub install hub://guardrails/detect_pii
# Also requires: presidio-analyzer and presidio-anonymizer
# Common PII entities: EMAIL_ADDRESS, PHONE_NUMBER, PERSON, LOCATION, CREDIT_CARD, SSN, etc.
# For full list see: https://microsoft.github.io/presidio/
_guard = Guard().use(
    DetectPII(
        pii_entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON", "LOCATION", "CREDIT_CARD", "SSN"],
        on_fail="noop",  # Don't raise exceptions, handle via state flags
    )
)


def guard_final(state: AgentState) -> AgentState:
    """
    Guard final node - Validates generated response for PII using Guardrails DetectPII.

    This node:
    1. Validates the generated_response using Guardrails DetectPII validator
    2. Sets is_risky flag if PII is detected
    3. Sets error_message if PII is found

    Args:
        state: Agent state containing the generated_response

    Returns:
        Updated state with is_risky and error_message set
    """
    updated_state = state.copy()
    generated_response = state.get("generated_response", "")

    if not generated_response:
        # Empty response is considered safe
        updated_state["is_risky"] = False
        updated_state["error_message"] = None
        return updated_state

    try:
        # Validate the generated response using Guardrails
        validation_result = _guard.validate(generated_response)

        # Check if validation passed
        # The validator returns ValidationResult with outcome
        # If validation fails, outcome will indicate failure
        if validation_result.validation_passed:
            updated_state["is_risky"] = False
            updated_state["error_message"] = None
            logger.debug("Generated response passed PII detection")
        else:
            # PII detected
            updated_state["is_risky"] = True
            updated_state["error_message"] = (
                "PII detected in response. The generated content contains personally identifiable information "
                "that cannot be shared."
            )
            logger.warning(f"PII detected in generated response: {generated_response[:100]}...")

    except Exception as e:
        # If validation fails due to error, log it but don't block the request
        # This is a safety measure - if Guardrails fails, we allow the request
        # but log the error for monitoring
        logger.error(f"Error during PII detection: {e}")
        updated_state["is_risky"] = False
        updated_state["error_message"] = None

    return updated_state
