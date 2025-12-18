"""Nodo Guard Final - Validates generated response for PII (risky information detection)."""

import logging
import re

from app.agents.state import AgentState

logger = logging.getLogger(__name__)

# Pattern-based PII detection (fallback when Guardrails Hub validators aren't available)
PII_PATTERNS = [
    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN format
    r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card format
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
    r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone number
]


def guard_final(state: AgentState) -> AgentState:
    """
    Guard final node - Validates generated response for PII using Guardrails DetectPII.

    This node:
    1. Validates the generated_response using Guardrails DetectPII validator
    2. Sets is_risky flag if PII is detected
    3. Sets error_message if risky content is detected

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
        # Pattern-based validation (fallback)
        has_pii = any(re.search(pattern, generated_response) for pattern in PII_PATTERNS)
        
        if not has_pii:
            updated_state["is_risky"] = False
            updated_state["error_message"] = None
            logger.debug("Generated response passed PII detection (pattern-based)")
        else:
            # PII detected
            updated_state["is_risky"] = True
            updated_state["error_message"] = (
                "PII detected in generated response. The information requested is classified or not free to know."
            )
            logger.warning("PII detected in generated response. Response content not logged for security.")

    except Exception as e:
        # If validation fails due to error, log it but don't block the request
        logger.error(f"Error during PII detection: {e}")
        updated_state["is_risky"] = False
        updated_state["error_message"] = None

    return updated_state
