"""
Chat Schemas Module.

This module defines the Pydantic models for chat message exchanges.
"""

from pydantic import BaseModel


class ChatMessage(BaseModel):
    """
    Schema for individual chat messages.
    """

    user_message: str


class ChatResponse(BaseModel):
    """
    Schema for AI-generated chat responses.
    """

    response: str


class MessageBody(BaseModel):
    """
    Schema for generic message payloads.
    """

    message: str
