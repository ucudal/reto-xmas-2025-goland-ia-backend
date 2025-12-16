from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class UserMessageIn(BaseModel):
    session_id: Optional[UUID] = None
    message: str


class AssistantMessageOut(BaseModel):
    session_id: UUID
    message: str
