"""Nodo 1: Agent Host - Entry point that prepares initial state."""

import logging

from app.agents.state import AgentState

logger = logging.getLogger(__name__)


def agent_host(state: AgentState) -> AgentState:
    """
    Agent Host node - Entry point for the agent flow.

    This node:
    1. Receives the initial prompt and optional chat_session_id
    2. Extracts the prompt from messages
    3. Prepares state for validation (no DB operations yet)
    
    Note: Chat history retrieval and message saving is deferred to parafraseo
    node to ensure malicious messages are not saved to the database.

    Args:
        state: Agent state containing the user prompt and optional chat_session_id

    Returns:
        Updated state with prompt and initial_context set (no DB operations)
    """
    updated_state = state.copy()
    
    # Extract prompt from messages
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    prompt = last_message.content if last_message else ""

    # Validate user_id is provided
    user_id = state.get("user_id")
    if not user_id:
        logger.error("user_id is required in state but was not provided")
        updated_state["error_message"] = "Se requiere user_id"
        return updated_state

    # Set prompt and initial context (no DB operations)
    updated_state["prompt"] = prompt
    updated_state["initial_context"] = prompt
    updated_state["chat_messages"] = None  # Will be set in parafraseo after validation

    logger.debug("Agent host prepared state for validation (no DB operations)")

    return updated_state
