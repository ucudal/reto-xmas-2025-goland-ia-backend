"""Nodo 1: Agent Host - Entry point that saves initial context."""

import logging

from app.agents.state import AgentState

logger = logging.getLogger(__name__)


def agent_host(state: AgentState) -> AgentState:
    """
    Agent Host node - Entry point for the agent flow.

    This node:
    1. Receives the initial prompt and optional chat_session_id
    2. Creates or retrieves chat session from PostgreSQL
    3. Saves the user's message to the chat session
    4. Retrieves all chat messages for the session
    5. Prepares state for validation

    Args:
        state: Agent state containing the user prompt and optional chat_session_id

    Returns:
        Updated state with chat_session_id, chat_messages, and initial_context set
    """
    updated_state = state.copy()
    initial_message = state["messages"][-1] if state["messages"] else None
    updated_state["initial_context"] = (
        initial_message.content if initial_message else ""
    )

    return updated_state
