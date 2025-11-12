from pydantic import BaseModel


class Dialog(BaseModel):
    conversationId: str
    content: str