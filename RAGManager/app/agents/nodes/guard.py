"""Nodo 2: Guard - Validates for malicious content."""

import logging

from guardrails import Guard
from guardrails.hub import DetectJailbreak

from app.agents.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Guard with DetectJailbreak validator
# Note: The validator must be installed via: guardrails hub install hub://guardrails/detect_jailbreak
_guard = Guard().use(
    DetectJailbreak(
        threshold=settings.guardrails_jailbreak_threshold,
        device=settings.guardrails_device,
        on_fail="noop",  # Don't raise exceptions, handle via state flags
    )
)


def guard(state: AgentState) -> AgentState:
    """
    Guard node - Validates user input for malicious content using Guardrails DetectJailbreak.

    This node:
    1. Validates the prompt using Guardrails DetectJailbreak validator
    2. Sets is_malicious flag if jailbreak attempt is detected
    3. Sets error_message if malicious content is detected

    Args:
        state: Agent state containing the prompt

    Returns:
        Updated state with is_malicious and error_message set
    """
    updated_state = state.copy()
    prompt = state.get("prompt", "")

    if not prompt:
        # Empty prompt is considered safe
        updated_state["is_malicious"] = False
        updated_state["error_message"] = None
        return updated_state

    try:
        # Validate the prompt using Guardrails
        validation_result = _guard.validate(prompt)

        # Check if validation passed
        # The validator returns ValidationResult with outcome
        # If validation fails, outcome will indicate failure
        if validation_result.validation_passed:
            updated_state["is_malicious"] = False
            updated_state["error_message"] = None
            logger.debug("Prompt passed jailbreak detection")
        else:
            # Jailbreak detected
            updated_state["is_malicious"] = True
            updated_state["error_message"] = (
                "Jailbreak attempt detected. Your request contains content that violates security policies."
            )
            logger.warning(f"Jailbreak attempt detected in prompt: {prompt[:100]}...")

    except Exception as e:
        # If validation fails due to error, log it but don't block the request
        # This is a safety measure - if Guardrails fails, we allow the request
        # but log the error for monitoring
        logger.error(f"Error during jailbreak detection: {e}")
        updated_state["is_malicious"] = False
        updated_state["error_message"] = None

    return updated_state
