"""Service functions for chat-related operations."""

import logging
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage

from app.models.chat import ChatMessage, ChatSession
from app.agents.graph import create_agent_graph
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


def get_chat_history(db: Session, session_id: UUID) -> list[ChatMessage]:
    """
    Retrieve the last 10 messages from a chat session.

    Args:
        db: SQLAlchemy database session
        session_id: UUID of the chat session

    Returns:
        List of ChatMessage objects ordered by created_at DESC (most recent first)

    Raises:
        ValueError: If the chat session doesn't exist
    """
    # First, validate that the session exists
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise ValueError(f"Chat session {session_id} not found")

    # Query the last 10 messages for this session, ordered by created_at DESC
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
        .all()
    )

    # Reverse to get chronological order (oldest first)
    # But the plan says "most recent first", so we'll keep DESC order
    logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
    return messages


async def process_message_with_agent(
    db: Session,
    message: str,
    session_id: Optional[UUID] = None,
) -> str:
    """
    Process a user message through the LangGraph agent.

    This function:
    1. Creates the initial state with the user message
    2. Runs the message through the complete agent graph
    3. Extracts and returns the generated response

    Args:
        db: SQLAlchemy database session
        message: User's message to process
        session_id: Optional UUID of the chat session (for history retrieval)

    Returns:
        Generated assistant response from the agent

    Raises:
        ValueError: If message is empty or agent fails with validation error
        Exception: For other processing errors
    """
    if not message or not message.strip():
        raise ValueError("Message cannot be empty")

    logger.info(f"Processing message through agent (session: {session_id})")

    try:
        # Create the agent graph
        agent_graph = create_agent_graph()

        # Prepare initial state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "prompt": message,
            "chat_session_id": str(session_id) if session_id else None,
            "user_id": None,  # Optional, can be added later if needed
            # Initialize other fields
            "initial_context": None,
            "chat_messages": None,
            "is_malicious": False,
            "error_message": None,
            "adjusted_text": None,
            "paraphrased_text": None,
            "paraphrased_statements": None,
            "relevant_chunks": None,
            "enriched_query": None,
            "primary_response": None,
            "generated_response": None,
            "is_risky": False,
            "final_response": None,
        }

        # Run the agent graph
        logger.info("Invoking agent graph")
        result = agent_graph.invoke(initial_state)

        # Extract the response from the result
        # Priority: final_response > generated_response > primary_response > error_message
        response = (
            result.get("final_response")
            or result.get("generated_response")
            or result.get("primary_response")
            or result.get("error_message")
            or "I'm sorry, I couldn't process your message."
        )

        logger.info(f"Agent processing completed successfully")
        return response

    except Exception as e:
        logger.error(f"Error in agent processing: {e}", exc_info=True)
        raise Exception(f"Failed to process message through agent: {str(e)}")


def save_user_message(db: Session, message: str, session_id: UUID | None = None) -> tuple[ChatMessage, UUID]:
    """
    Save a user message to a chat session.

    Args:
        db: SQLAlchemy database session
        message: The user's message text
        session_id: UUID of the chat session (optional - creates new session if not provided)

    Returns:
        Tuple of (saved ChatMessage object, session_id UUID)

    Raises:
        ValueError: If the provided session_id doesn't exist
    """
    # 1. If no session_id provided, create a new session
    if not session_id:
        session = ChatSession()
        db.add(session)
        db.flush()  # Generate UUID without committing
        session_id = session.id
        logger.info(f"Created new chat session: {session_id}")
    else:
        # Validate that the session exists
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise ValueError(f"Chat session {session_id} not found")

    # 2. Create and save the user message
    user_message = ChatMessage(
        session_id=session_id,
        sender="user",
        message=message
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    logger.info(f"Saved user message to session {session_id}")
    return user_message, session_id
