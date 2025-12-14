"""Nodo 2: Guard Inicial - Validates for malicious content (jailbreak detection)."""

import logging

from guardrails import Guard
from guardrails.hub import DetectJailbreak

from app.agents.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Guard with DetectJailbreak validator
# Note: The validator must be installed via: guardrails hub install hub://guardrails/detect_jailbreak
_guard: Guard | None = None

def _get_guard() -> Guard:
    global _guard
    if _guard is None:
        _guard = Guard().use(
            DetectJailbreak(
                threshold=settings.guardrails_jailbreak_threshold,
                device=settings.guardrails_device,
                on_fail="noop",
            )
        )
    return _guard


def guard_inicial(state: AgentState) -> AgentState:
    """
    Guard inicial node - Validates user input for malicious content using Guardrails DetectJailbreak.

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
    if state["messages"]:
        last_message = state["messages"][-1]
        prompt = last_message.content if last_message else ""
    else:
        last_message = None
        prompt = ""

    if not prompt:
        # Empty prompt is considered safe
        updated_state["is_malicious"] = False
        updated_state["error_message"] = None
        return updated_state

    try:
        # Validate the prompt using Guardrails
        validation_result = _get_guard().validate(prompt)

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
            logger.warning(
                "Jailbreak attempt detected in prompt",
                extra={"prompt_len": len(prompt)},
            )

    except Exception as e:
        # Log error details for monitoring
        logger.error("Error during jailbreak detection", exc_info=True)

        # Check if fail-closed mode is enabled
        if settings.guardrails_fail_closed:
            # Fail-closed: treat errors as malicious to prevent bypassing detection
            updated_state["is_malicious"] = True
            updated_state["error_message"] = f"Jailbreak detection error: {str(e)}"
        else:
            # Fail-open: allow requests when Guardrails fails (backward compatibility)
            updated_state["is_malicious"] = False
            updated_state["error_message"] = None

    return updated_state
