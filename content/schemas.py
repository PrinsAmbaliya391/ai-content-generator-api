<<<<<<< HEAD
"""
Content Schemas Module.

This module defines the Pydantic models for content generation,
refinement, and update requests.
"""

=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
from pydantic import BaseModel


class ContentRequest(BaseModel):
<<<<<<< HEAD
    """
    Schema for initial AI content generation requests.
    """

=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    topic: str
    word_count: int
    tone: str
    language: str


class UpdateRequest(BaseModel):
<<<<<<< HEAD
    """
    Schema for manual content update requests.
    """

    generations_uuid: str
=======
    generation_id: int
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    updated_text: str


class RefineRequest(BaseModel):
<<<<<<< HEAD
    """
    Schema for AI-powered content refinement requests.
    """

    generations_uuid: str
=======
    generation_id: int
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    user_change: str
    disliked_part: str


class RegenerateRequest(BaseModel):
<<<<<<< HEAD
    """
    Schema for AI content regeneration requests.
    """

    generations_uuid: str
=======
    generation_id: int
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
