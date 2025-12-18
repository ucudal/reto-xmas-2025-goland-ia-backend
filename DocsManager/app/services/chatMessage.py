from sqlalchemy.orm import Session
from typing import AsyncIterator
from uuid import uuid4, UUID

from app.models.chat_message import ChatMessage
from app.schemas.enums.sender_type import SenderType
from app.models.chat_session import ChatSession
from ag_ui.core import (
    RunAgentInput,
    RunStartedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    RunFinishedEvent,
    MessagesSnapshotEvent,
    AssistantMessage,
    TextInputContent
)
from ag_ui.encoder import (
    EventEncoder
)


def assistant_reply(text: str) -> str:
    return f"Respuesta del asistente a: {text}"


def create_user_message(
    db: Session,
    message: str,
    session_id=None
):
    # 1. Si no hay session_id → crear sesión nueva
    if not session_id:
        session = ChatSession()
        db.add(session)
        db.flush()  # genera el UUID sin commit
        session_id = session.id
    else:
        # Convertir session_id a UUID si es string
        try:
            if isinstance(session_id, str):
                session_uuid = UUID(session_id)
            else:
                session_uuid = session_id
            
            # Intentar obtener la sesión existente
            session = db.get(ChatSession, session_uuid)
            if not session:
                # Si el thread_id no existe, crear una nueva sesión
                # Nota: No podemos forzar el ID, PostgreSQL lo generará automáticamente
                # En su lugar, creamos una nueva sesión y el frontend deberá usar el nuevo ID
                session = ChatSession()
                db.add(session)
                db.flush()
                session_id = session.id
        except (ValueError, TypeError):
            # Si el session_id no es un UUID válido, crear una nueva sesión
            session = ChatSession()
            db.add(session)
            db.flush()
            session_id = session.id

    # 2. Guardar mensaje del usuario
    user_msg = ChatMessage(
        session_id=session_id,
        sender=SenderType.user,
        message=message
    )
    db.add(user_msg)

    # 3. Respuesta del asistente
    assistant_text = assistant_reply(message)

    assistant_msg = ChatMessage(
        session_id=session_id,
        sender=SenderType.assistant,
        message=assistant_text
    )
    db.add(assistant_msg)

    db.commit()
    db.refresh(assistant_msg)

    return assistant_msg, session_id


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
        # Note: role parameter may not be supported, using only required fields
        try:
            text_start = TextMessageStartEvent(
                run_id=payload.run_id,
                message_id=message_id,
                role="assistant"
            )
        except TypeError:
            # If role is not supported, create without it
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
        # Note: AssistantMessage content should be a string, not a list
        try:
            messages_snapshot = MessagesSnapshotEvent(
                run_id=payload.run_id,
                messages=[
                    *payload.messages,  # Include previous messages
                    AssistantMessage(
                        id=message_id,
                        content=assistant_msg.message  # String, not list
                    )
                ]
            )
            yield encoder.encode(messages_snapshot)
        except Exception as e:
            # If MESSAGES_SNAPSHOT fails, log but continue to RUN_FINISHED
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to create MESSAGES_SNAPSHOT: {e}")
            # Continue to RUN_FINISHED anyway
        
        # Emit RUN_FINISHED event
        # Note: thread_id parameter may not be supported, using only required fields
        try:
            run_finished = RunFinishedEvent(
                run_id=payload.run_id,
                thread_id=payload.thread_id
            )
        except TypeError:
            # If thread_id is not supported, create without it
            run_finished = RunFinishedEvent(
                run_id=payload.run_id
            )
        yield encoder.encode(run_finished)
        
        # Ensure stream is properly closed by yielding empty string at the end
        # This helps ensure all data is flushed
        yield ""
        
    except Exception as e:
        # In case of error, emit error information and close stream properly
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error processing agent message: {e}", exc_info=True)
        # Try to emit an error event if possible, otherwise just close
        # The stream will be closed automatically when the generator exits
        raise