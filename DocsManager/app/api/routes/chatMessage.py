from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db_connection import get_sessionmaker
from app.schemas.chatMessage import UserMessageIn, AssistantMessageOut
from app.services.chatMessage import create_user_message

SessionMaker = get_sessionmaker()


def get_db():
    db = SessionMaker()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post(
    "/messages",
    response_model=AssistantMessageOut
)
def post_user_message(
    payload: UserMessageIn,
    db: Session = Depends(get_db)
):
    assistant_msg, session_id = create_user_message(
        db=db,
        message=payload.message,
        session_id=payload.session_id
    )

    return {
        "session_id": session_id,
        "message": assistant_msg.message
    }
