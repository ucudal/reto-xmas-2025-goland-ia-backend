from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.schemas.enums.sender_type import SenderType
from app.models.chat_session import ChatSession

def assistant_reply(text: str) -> str:
    return f"Respuesta del asistente a: {text}"


def create_user_message(
    db: Session,
    message: str,
    session_id=None
):
    # 1. Si no hay session_id → crear sesión nueva
    if session_id is None:
        session = ChatSession()
        db.add(session)
        db.flush()  # genera el UUID sin commit
        session_id = session.id
    else:
        session = db.get(ChatSession, session_id)
        if not session:
            raise ValueError("Chat session not found")

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