"""
Content Generation Routes Module.

This module defines the API endpoints for creating, refining,
regenerating, and managing AI-generated content.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from content.schemas import (
    ContentRequest,
    UpdateRequest,
    RefineRequest,
    RegenerateRequest,
)
from content.services import content_service as ContentService
from core.security import get_current_user
from typing import Optional

router = APIRouter(prefix="/content", tags=["Content"])


@router.post("/generate")
async def create_content(
    topic: str = Form(...),
    word_count: int = Form(...),
    tone: str = Form(...),
    language: str = Form(...),
    file: Optional[UploadFile] = File(None),
    user_uuid: str = Depends(get_current_user),
):
    """
    Generates new AI content based on a topic and optional document context (RAG).

    Args:
        topic (str): The subject of the content.
        word_count (int): Target length of the generated text.
        tone (str): Desired writing style (e.g., formal, casual).
        language (str): Target language.
        file (UploadFile, optional): Document for RAG context.
        user_uuid (str): Identity of the authenticated user.

    Returns:
        dict: Generated content and metadata.
    """
    req = ContentRequest(
        topic=topic, word_count=word_count, tone=tone, language=language
    )
    return await ContentService.generate(req, user_uuid, file)


@router.get("/history")
async def get_history(user_uuid: str = Depends(get_current_user)):
    """
    Retrieves the complete generation history for the authenticated user, including all versions.

    Args:
        user_uuid (str): Identity of the authenticated user.

    Returns:
        dict: List of previous generation records.
    """
    return await ContentService.get_history(user_uuid)


@router.delete("/delete/{generations_uuid}")
async def delete_content(
    generations_uuid: str, user_uuid: str = Depends(get_current_user)
):
    """
    Permanently deletes a specific generation record and its history.

    Args:
        generations_uuid (str): External identifier for the generation.
        user_uuid (str): Identity of the authenticated user.

    Returns:
        dict: Confirmation message.
    """
    return await ContentService.delete(generations_uuid, user_uuid)


@router.post("/update")
async def update_content(
    req: UpdateRequest, user_uuid: str = Depends(get_current_user)
):
    """
    Saves a manually updated version of the generated content.

    Args:
        req (UpdateRequest): Contains the UUID and the updated text.
        user_uuid (str): Identity of the authenticated user.

    Returns:
        dict: Status of the update.
    """
    return await ContentService.update_content(req, user_uuid)


@router.post("/refine")
async def refine_content(
    req: RefineRequest, user_uuid: str = Depends(get_current_user)
):
    """
    Refines existing content using AI based on user feedback.

    Args:
        req (RefineRequest): Contains the UUID and specific refinement instructions.
        user_uuid (str): Identity of the authenticated user.

    Returns:
        dict: The refined content.
    """
    return await ContentService.refine_content(req, user_uuid)


@router.post("/regenerate")
async def regenerate_content(
    req: RegenerateRequest, user_uuid: str = Depends(get_current_user)
):
    """
    Regenerates a completely new AI response for a given topic and context.

    Args:
        req (RegenerateRequest): Contains the UUID of the generation to rewrite.
        user_uuid (str): Identity of the authenticated user.

    Returns:
        dict: The newly generated content.
    """
    return await ContentService.regenerate_content(req, user_uuid)
