"""Nodo 2: Guard Inicial - Validates for malicious content (jailbreak detection)."""

import logging

from app.agents.state import AgentState

logger = logging.getLogger(__name__)

# Simplified jailbreak detection for testing
# TODO: Replace with full Guardrails implementation once validators are installed:
# guardrails hub install hub://guardrails/detect_jailbreak
JAILBREAK_PATTERNS = [
    "ignore all previous instructions",
    "ignore previous instructions",
    "disregard all previous",
    "forget everything",
    "reveal sensitive",
    "bypass restrictions",
    "system prompt",
    "act as",
    "pretend you are",
]


def guard_inicial(state: AgentState) -> AgentState:
    """
    Guard inicial node - Validates user input for jailbreak attempts using Guardrails DetectJailbreak.

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
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    prompt = last_message.content if last_message else ""

    if not prompt:
        # Empty prompt is considered safe
        updated_state["is_malicious"] = False
        updated_state["error_message"] = None
        return updated_state

    try:
        # Simplified validation - check for jailbreak patterns
        # TODO: Replace with full Guardrails implementation
        prompt_lower = prompt.lower()
        is_jailbreak = any(pattern in prompt_lower for pattern in JAILBREAK_PATTERNS)
        
        if not is_jailbreak:
            updated_state["is_malicious"] = False
            updated_state["error_message"] = None
            logger.debug("Prompt passed jailbreak detection (simplified)")
        else:
            # Jailbreak detected
            updated_state["is_malicious"] = True
            updated_state["error_message"] = (
                "Jailbreak attempt detected. Your request contains content that violates security policies."
            )
            logger.warning("Jailbreak attempt detected. Prompt content not logged for security.")

    except Exception as e:
        # If validation fails due to error, log it but don't block the request
        logger.error(f"Error during jailbreak detection: {e}")
        updated_state["is_malicious"] = False
        updated_state["error_message"] = None

    return updated_state
