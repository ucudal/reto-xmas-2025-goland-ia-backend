"""Nodo 4: Parafraseo - Saves message, retrieves chat history, and paraphrases user input."""

import logging

from app.agents.state import AgentState
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

llm = ChatOpenAI(model="gpt-5-nano")


def parafraseo(state: AgentState) -> AgentState:
    """
    Parafraseo node - Saves message to DB, retrieves chat history, and paraphrases user input.

    This node:
    1. Saves the user's message to the chat session in PostgreSQL
    2. Retrieves all chat messages for the session (including the newly saved message)
    3. Paraphrases the user input using chat history to improve clarity
    4. Prepares text for retrieval step

    Args:
        state: Agent state containing prompt, chat_session_id, and user_id

    Returns:
        Updated state with chat_messages, paraphrased_text set
    """
    updated_state = state.copy()
    
    # TODO: Implement endpoint call to save message and retrieve chat history
    # This should:
    # 1. Call an endpoint (not yet developed) that:
    #    - Saves the current user message to the chat session
    #    - Retrieves all chat messages for the session (including the newly saved message)
    #    - Returns the updated chat_messages list
    # 2. Update state with chat_messages from the endpoint response
    # 3. Handle errors appropriately (session not found, permission denied, etc.)
    
    # Placeholder: For now, we'll use empty chat history
    # Once the endpoint is implemented, replace this with the actual endpoint call
    updated_state["chat_messages"] = None
    logger.warning("Chat history retrieval endpoint not yet implemented - using empty history")
    
    # Paraphrase the last message using history
    system_instruction = """You are an expert at paraphrasing user questions to be standalone and clear, given the conversation history.
Reformulate the last user message to be a self-contained query that includes necessary context from previous messages.
Do not answer the question, just rewrite it."""

    # Use messages from state (will include chat history once endpoint is implemented)
    messages = [SystemMessage(content=system_instruction)] + state.get("messages", [])
    
    response = llm.invoke(messages)
    updated_state["paraphrased_text"] = response.content

    return updated_state
