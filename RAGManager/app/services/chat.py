"""Service functions for chat-related operations."""

import logging
from uuid import UUID
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage

from app.models.chat import ChatMessage, ChatSession
from app.repositories.chat_repository import get_chat_history
from app.agents.graph import create_agent_graph
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


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


def create_user_message_and_process(
    db: Session,
    message: str,
    session_id: Optional[UUID] = None,
) -> Tuple[ChatMessage, UUID]:
    """
    Complete flow: save user message, process through agent, save assistant response.
    
    This function handles the entire chat flow:
    1. Creates or retrieves a chat session
    2. Saves the user's message to the database
    3. Processes the message through the LangGraph agent
    4. Saves the assistant's response to the database
    5. Returns the assistant message and session_id
    
    Args:
        db: Database session
        message: User's message text
        session_id: Optional existing session ID
        
    Returns:
        Tuple of (assistant_msg, session_id)
        
    Raises:
        ValueError: If session_id provided but doesn't exist
        Exception: For processing or database errors
    """
    # 1. Create or retrieve session
    if not session_id:
        session = ChatSession()
        db.add(session)
        db.flush()  # Generate UUID without commit
        session_id = session.id
        logger.info(f"Created new chat session: {session_id}")
    else:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise ValueError(f"Chat session {session_id} not found")
        logger.info(f"Using existing chat session: {session_id}")

    # 2. Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        sender="user",
        message=message
    )
    db.add(user_msg)
    db.commit()  # Commit user message first
    logger.info(f"Saved user message to database (session: {session_id})")
    
    try:
        # 3. Process message through agent
        # Note: We need to use asyncio for async function
        import asyncio
        
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        assistant_text = loop.run_until_complete(
            process_message_with_agent(db, message, session_id)
        )
        
        logger.info(f"Agent generated response (session: {session_id})")
        
    except Exception as e:
        logger.error(f"Error getting response from agent: {e}", exc_info=True)
        # Fallback response in case of error
        assistant_text = "I'm sorry, I'm having trouble processing your request right now. Please try again later."

    # 4. Save assistant response
    assistant_msg = ChatMessage(
        session_id=session_id,
        sender="assistant",
        message=assistant_text
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    
    logger.info(f"Saved assistant response to database (session: {session_id})")

    return assistant_msg, session_id

