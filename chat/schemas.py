<<<<<<< HEAD
"""
Chat Schemas Module.

This module defines the Pydantic models for chat message exchanges.
"""

=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
from pydantic import BaseModel


class ChatMessage(BaseModel):
<<<<<<< HEAD
    """
    Schema for individual chat messages.
    """

=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    user_message: str


class ChatResponse(BaseModel):
<<<<<<< HEAD
    """
    Schema for AI-generated chat responses.
    """

=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    response: str


class MessageBody(BaseModel):
<<<<<<< HEAD
    """
    Schema for generic message payloads.
    """

    message: str
=======
    message: str
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
