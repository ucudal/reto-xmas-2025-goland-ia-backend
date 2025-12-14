"""Nodo Guard Final - Validates generated response for PII (Personally Identifiable Information)."""

import logging
from typing import TYPE_CHECKING

from app.agents.state import AgentState

if TYPE_CHECKING:
    from guardrails import Guard

logger = logging.getLogger(__name__)

# Lazy initialization of Guard with DetectPII validator
# Note: The validator must be installed via: guardrails hub install hub://guardrails/detect_pii
# Also requires: presidio-analyzer and presidio-anonymizer
# Common PII entities: EMAIL_ADDRESS, PHONE_NUMBER, PERSON, LOCATION, CREDIT_CARD, SSN, etc.
# For full list see: https://microsoft.github.io/presidio/
_guard: "Guard | None" = None


def _get_guard() -> "Guard":
    """Lazy initialization of Guard with DetectPII validator to prevent import-time crashes."""
    global _guard
    if _guard is None:
        from guardrails import Guard
        from guardrails.hub import DetectPII

        _guard = Guard().use(
            DetectPII(
                pii_entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON", "LOCATION", "CREDIT_CARD", "SSN"],
                on_fail="noop",  # Don't raise exceptions, handle via state flags
            )
        )
    return _guard


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
    generated_response = state["messages"][-1].content if state.get("messages") else ""

    if not generated_response:
        # Empty response is considered safe
        updated_state["is_risky"] = False
        updated_state["error_message"] = None
        return updated_state

    try:
        # Validate the generated response using Guardrails
        validation_result = _get_guard().validate(generated_response)

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
            logger.warning(
                "PII detected in generated response",
                extra={"response_len": len(generated_response)},
            )

    except Exception as e:
        # Fail-closed: If validation fails due to error, treat as risky
        # This prevents bypassing PII detection through errors
        logger.error("Error during PII detection", exc_info=True)
        updated_state["is_risky"] = True
        updated_state["error_message"] = f"PII detection error: {str(e)}"

    return updated_state
