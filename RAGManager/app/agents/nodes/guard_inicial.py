"""Nodo 2: Guard Inicial - Validates for malicious content (jailbreak detection)."""

import logging

# Guardrails disabled for now
# from guardrails import Guard
# from guardrails.hub import DetectJailbreak, ToxicLanguage

from app.agents.state import AgentState
# from app.core.config import settings

logger = logging.getLogger(__name__)

# Guardrails disabled for now - just pass through
# # Initialize Guard with DetectJailbreak and ToxicLanguage validators
# # Note: The validators must be installed via:
# #   guardrails hub install hub://guardrails/detect_jailbreak
# #   guardrails hub install hub://guardrails/toxic_language
# _guard_inicial = Guard().use(
#     DetectJailbreak(
#         threshold=settings.guardrails_jailbreak_threshold,
#         device=settings.guardrails_device,
#         on_fail="noop",  # Don't raise exceptions, handle via state flags
#     )
# ).use(
#     ToxicLanguage(
#         on_fail="noop",  # Don't raise exceptions, handle via state flags
#     )
# )


def guard_inicial(state: AgentState) -> AgentState:
    """
    Guard inicial node - Validates user input for jailbreak attempts and toxic language using Guardrails.

    This node:
    1. Validates the prompt using Guardrails DetectJailbreak and ToxicLanguage validators
    2. Sets is_malicious flag if jailbreak attempt or toxic language is detected
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

    # Guardrails disabled for now - just pass through
    updated_state["is_malicious"] = False
    updated_state["error_message"] = None
    logger.debug("Guardrails disabled - prompt passed through without validation")
    
    # try:
    #     # Validate the prompt using Guardrails
    #     validation_result = _guard_inicial.validate(prompt)
    #
    #     # Check if validation passed
    #     # The validator returns ValidationResult with outcome
    #     # If validation fails, outcome will indicate failure
    #     if validation_result.validation_passed:
    #         updated_state["is_malicious"] = False
    #         updated_state["error_message"] = None
    #         logger.debug("Prompt passed jailbreak and toxic language detection")
    #     else:
    #         # Jailbreak or toxic language detected
    #         updated_state["is_malicious"] = True
    #         updated_state["error_message"] = (
    #             "Contenido malicioso detectado. Tu solicitud contiene contenido que viola las políticas de seguridad."
    #         )
    #         logger.warning("Malicious content detected. Prompt content not logged for security.")
    #
    # except Exception as e:
    #     # If validation fails due to error, log it but don't block the request
    #     # This is a safety measure - if Guardrails fails, we allow the request
    #     # but log the error for monitoring
    #     logger.error(f"Error during jailbreak detection: {e}")
    #     updated_state["is_malicious"] = False
    #     updated_state["error_message"] = None

    return updated_state
