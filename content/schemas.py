"""
Content Schemas Module.

This module defines the Pydantic models for content generation,
refinement, and update requests.
"""

from pydantic import BaseModel


class ContentRequest(BaseModel):
    """
    Schema for initial AI content generation requests.
    """

    topic: str
    word_count: int
    tone: str
    language: str


class UpdateRequest(BaseModel):
    """
    Schema for manual content update requests.
    """

    generations_uuid: str
    updated_text: str


class RefineRequest(BaseModel):
    """
    Schema for AI-powered content refinement requests.
    """

    generations_uuid: str
    user_change: str
    disliked_part: str


class RegenerateRequest(BaseModel):
    """
    Schema for AI content regeneration requests.
    """

    generations_uuid: str
