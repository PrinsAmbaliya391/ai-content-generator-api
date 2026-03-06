from pydantic import BaseModel


class ChatMessage(BaseModel):
    user_message: str


class ChatResponse(BaseModel):
    response: str


class MessageBody(BaseModel):
    message: str