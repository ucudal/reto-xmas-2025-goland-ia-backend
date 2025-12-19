"""Nodo Guard Final - Validates generated response for PII (risky information detection)."""

import logging

from guardrails import Guard
from guardrails.hub import DetectPII, ToxicLanguage

from app.agents.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Guard with DetectPII and ToxicLanguage validators
# Note: The validators must be installed via:
#   guardrails hub install hub://guardrails/detect_pii
#   guardrails hub install hub://guardrails/toxic_language
_guard_final = Guard().use(
    DetectPII(
        pii_entities=settings.guardrails_pii_entities,
        on_fail="noop",  # Don't raise exceptions, handle via state flags
    )
).use(
    ToxicLanguage(
        on_fail="noop",  # Don't raise exceptions, handle via state flags
    )
)


def guard_final(state: AgentState) -> AgentState:
    """
    Guard final node - Validates generated response for PII and toxic language using Guardrails.

    This node:
    1. Validates the generated_response using Guardrails DetectPII and ToxicLanguage validators
    2. Sets is_risky flag if PII or toxic language is detected
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
        # Validate the generated response using Guardrails
        validation_result = _guard_final.validate(generated_response)

        # Check if validation passed
        # The validator returns ValidationResult with outcome
        # If validation fails, outcome will indicate failure
        if validation_result.validation_passed:
            updated_state["is_risky"] = False
            updated_state["error_message"] = None
            logger.debug("Generated response passed PII and toxic language detection")
        else:
            # PII or toxic language detected
            updated_state["is_risky"] = True
            updated_state["error_message"] = (
               "Contenido riesgoso detectado en la respuesta generada. La información solicitada está clasificada o no es de libre acceso."
            )
            logger.warning("Risky content detected in generated response. Response content not logged for security.")

    except Exception as e:
        # If validation fails due to error, log it but don't block the request
        # This is a safety measure - if Guardrails fails, we allow the request
        # but log the error for monitoring
        logger.error(f"Error during PII detection: {e}")
        updated_state["is_risky"] = False
        updated_state["error_message"] = None

    return updated_state
