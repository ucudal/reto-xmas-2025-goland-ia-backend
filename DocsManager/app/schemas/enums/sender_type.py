import enum

class SenderType(enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"