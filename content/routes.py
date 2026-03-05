from fastapi import APIRouter, Depends
from content.schemas import (
    ContentRequest,
    UpdateRequest,
    RefineRequest,
    RegenerateRequest,
)
from content.services import ContentService
from core.security import get_current_user

router = APIRouter(prefix="/content", tags=["Content"])


@router.post("/generate")
async def create_content(
    req: ContentRequest, user_uuid: str = Depends(get_current_user)
):
    return await ContentService.generate(req, user_uuid)


@router.get("/history")
async def get_history(user_uuid: str = Depends(get_current_user)):
    return await ContentService.get_history(user_uuid)


@router.delete("/delete/{id}")
async def delete_content(id: int, user_uuid: str = Depends(get_current_user)):
    return await ContentService.delete(id, user_uuid)


@router.post("/update")
async def update_content(
    req: UpdateRequest, user_uuid: str = Depends(get_current_user)
):
    return await ContentService.update_content(req, user_uuid)


@router.post("/refine")
async def refine_content(
    req: RefineRequest, user_uuid: str = Depends(get_current_user)
):
    return await ContentService.refine_content(req, user_uuid)


@router.post("/regenerate")
async def regenerate_content(
    req: RegenerateRequest, user_uuid: str = Depends(get_current_user)
):
    return await ContentService.regenerate_content(req, user_uuid)
