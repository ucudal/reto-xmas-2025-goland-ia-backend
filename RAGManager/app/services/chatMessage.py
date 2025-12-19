import logging
from typing import AsyncIterator
from uuid import UUID as UUIDType, uuid4

from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

from ag_ui.core import (
    AssistantMessage,
    MessagesSnapshotEvent,
    RunAgentInput,
    RunFinishedEvent,
    RunStartedEvent,
    TextInputContent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from ag_ui.encoder import EventEncoder

from app.agents.graph import create_agent_graph
from app.agents.state import AgentState
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.schemas.enums.sender_type import SenderType

logger = logging.getLogger(__name__)


def assistant_reply(text: str, session_id: str | None = None) -> tuple[str, str | None]:
    """
    Invoke the agent graph with the user message and return the assistant's reply and session_id.
    
    Args:
        text: The user's message text
        session_id: Optional chat session ID for context
        
    Returns:
        Tuple of (assistant_response_text, session_id)
        The session_id may be updated if the graph created a new session
    """
    try:
        # Create and compile the agent graph
        graph = create_agent_graph()
        
        # Build initial state for the graph
        # Note: AgentState extends MessagesState, so 'messages' is inherited
        initial_state: AgentState = {
            "messages": [HumanMessage(content=text)],
            "prompt": text,  # Required field
            "chat_session_id": session_id,  # Optional
            "user_id": None,  # Optional
            "initial_context": None,  # Optional
            "chat_messages": None,  # Optional
            "is_malicious": False,  # Required field
            "error_message": None,  # Optional
            "adjusted_text": None,  # Optional
            "paraphrased_text": None,  # Optional
            "paraphrased_statements": None,  # Optional
            "relevant_chunks": None,  # Optional
            "enriched_query": None,  # Optional
            "primary_response": None,  # Optional
            "generated_response": None,  # Optional
            "is_risky": False,  # Required field
            "final_response": None,  # Optional
        }
        
        # Invoke the graph
        final_state = graph.invoke(initial_state)
        
        # Extract the response - prefer final_response (from fallback) or generated_response (from context_builder)
        response = final_state.get("final_response") or final_state.get("generated_response")
        
        if not response:
            # Fallback to error message or default response
            response = final_state.get("error_message") or "Lo siento, no pude generar una respuesta."
        
        # Get the session_id from the final state (may have been created by parafraseo node)
        updated_session_id = final_state.get("chat_session_id")
        
        return response, updated_session_id
        
    except Exception as e:
        # Log error and return a safe fallback message
        logger.error(f"Error invoking agent graph: {e}", exc_info=True)
        return f"Error al procesar tu mensaje: {str(e)}", session_id


def create_user_message(
    db: Session,
    message: str,
    session_id=None
):
    """
    Process user message through the agent graph and save assistant response.
    
    Note: The user message is saved by the graph's parafraseo node, not here.
    This function only saves the assistant's response after the graph completes.
    
    Args:
        db: Database session
        message: The user's message text
        session_id: Optional chat session ID (UUID object or string)
        
    Returns:
        Tuple of (assistant ChatMessage, session_id)
    """
    # 1. Validate and convert session_id to string if it's a valid UUID
    # If it's not a valid UUID, pass None and let the graph create a new session
    session_id_str = None
    if session_id:
        try:
            # Try to validate if it's a UUID (either string or UUID object)
            if isinstance(session_id, UUIDType):
                session_id_str = str(session_id)
            else:
                # Try to parse as UUID to validate
                UUIDType(session_id)
                session_id_str = str(session_id)
        except (ValueError, TypeError):
            # Not a valid UUID, will create a new session
            logger.warning(f"Invalid UUID format for session_id: {session_id}. Creating new session.")
            session_id_str = None
    
    # 2. Invoke agent graph - this will:
    #    - Save the user message via parafraseo node (which may create a new session)
    #    - Generate the assistant response through the full graph flow
    assistant_text, updated_session_id = assistant_reply(message, session_id=session_id_str)
    
    # 3. Use the session_id from the graph (may have been created by parafraseo node)
    # Convert back to UUID if needed
    if updated_session_id:
        try:
            final_session_id = UUIDType(updated_session_id) if isinstance(updated_session_id, str) else updated_session_id
        except (ValueError, TypeError):
            # Fallback: query for the most recent session (created by parafraseo)
            session = db.query(ChatSession).order_by(ChatSession.created_at.desc()).first()
            if session:
                final_session_id = session.id
            else:
                raise ValueError("Could not determine session_id after graph execution")
    else:
        # Fallback: query for the most recent session (created by parafraseo)
        session = db.query(ChatSession).order_by(ChatSession.created_at.desc()).first()
        if session:
            final_session_id = session.id
        else:
            raise ValueError("Could not determine session_id after graph execution")
    
    # 4. Save the assistant's response
    assistant_msg = ChatMessage(
        session_id=final_session_id,
        sender=SenderType.assistant,
        message=assistant_text
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return assistant_msg, final_session_id


async def process_agent_message(
    db: Session,
    payload: RunAgentInput
) -> AsyncIterator[str]:
    """Process agent message and generate AG-UI protocol events.
    
    Args:
        db: Database session
        payload: RunAgentInput containing the user's message and context
        
    Yields:
        AG-UI protocol events as encoded strings
    """
    encoder = EventEncoder()
    
    try:
        # Extract the user message from the messages list
        user_message_text = ""
        if payload.messages:
            last_message = payload.messages[-1]
            if hasattr(last_message, 'content'):
                if isinstance(last_message.content, list) and len(last_message.content) > 0:
                    user_message_text = last_message.content[0].text
                elif isinstance(last_message.content, str):
                    user_message_text = last_message.content
        
        # Use thread_id as session_id (AG-UI uses thread_id for conversation tracking)
        session_id = payload.thread_id if hasattr(payload, 'thread_id') else None

        if not payload.run_id:
            payload.run_id = str(uuid4())
        
        # Emit RUN_STARTED event
        run_started = RunStartedEvent(
            run_id=payload.run_id,
            thread_id=payload.thread_id
        )
        yield encoder.encode(run_started)
        
        # Process the message through the service
        assistant_msg, session_id = create_user_message(
            db=db,
            message=user_message_text,
            session_id=session_id
        )
        
        # Generate a unique message ID for the assistant response
        message_id = f"msg_{payload.run_id}"
        
        # Emit TEXT_MESSAGE_START event
        text_start = TextMessageStartEvent(
            run_id=payload.run_id,
            message_id=message_id
        )
        yield encoder.encode(text_start)
        
        # Emit TEXT_MESSAGE_CONTENT event with the assistant's response
        text_content = TextMessageContentEvent(
            run_id=payload.run_id,
            message_id=message_id,
            delta=assistant_msg.message
        )
        yield encoder.encode(text_content)
        
        # Emit TEXT_MESSAGE_END event
        text_end = TextMessageEndEvent(
            run_id=payload.run_id,
            message_id=message_id
        )
        yield encoder.encode(text_end)
        
        # Emit MESSAGES_SNAPSHOT event with the full conversation
        messages_snapshot = MessagesSnapshotEvent(
            run_id=payload.run_id,
            messages=[
                *payload.messages,  # Include previous messages
                AssistantMessage(
                    id=message_id,
                    content=assistant_msg.message  # content should be a string, not a list
                )
            ]
        )
        yield encoder.encode(messages_snapshot)
        
        # Emit RUN_FINISHED event
        run_finished = RunFinishedEvent(
            run_id=payload.run_id,
            thread_id=payload.thread_id
        )
        yield encoder.encode(run_finished)
        
    except Exception as e:
        # In case of error, we should emit a RUN_ERROR event
        # For now, we'll just re-raise the exception
        raise