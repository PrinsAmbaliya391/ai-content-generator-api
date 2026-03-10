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
    """
    req = ContentRequest(
        topic=topic, word_count=word_count, tone=tone, language=language
    )
    return await ContentService.generate(req, user_uuid, file)


@router.get("/history")
async def get_history(user_uuid: str = Depends(get_current_user)):
    """
    Retrieves the generation history for the authenticated user.
    """
    return await ContentService.get_history(user_uuid)


@router.delete("/delete/{generations_uuid}")
async def delete_content(generations_uuid: str, user_uuid: str = Depends(get_current_user)):
    """
    Deletes a specific generation record.
    """
    return await ContentService.delete(generations_uuid, user_uuid)


@router.post("/update")
async def update_content(
    req: UpdateRequest, user_uuid: str = Depends(get_current_user)
):
    """
    Appends manual edits to an existing content record.
    """
    return await ContentService.update_content(req, user_uuid)


@router.post("/refine")
async def refine_content(
    req: RefineRequest, user_uuid: str = Depends(get_current_user)
):
    """
    Refines existing content using AI feedback.
    """
    return await ContentService.refine_content(req, user_uuid)


@router.post("/regenerate")
async def regenerate_content(
    req: RegenerateRequest, user_uuid: str = Depends(get_current_user)
):
    """
    Regenerates a completely new version of the content.
    """
    return await ContentService.regenerate_content(req, user_uuid)
