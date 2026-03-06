from fastapi import APIRouter, WebSocket
from chat.services import chat_service as ChatService

router = APIRouter(prefix="/chat")


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    await ChatService.handle_websocket(websocket)


@router.websocket("/system")
async def websocket_system(websocket: WebSocket):
    await ChatService.system_chat(websocket)


@router.websocket("/continue/{session_id}")
async def websocket_continue(websocket: WebSocket, session_id: str):
    await ChatService.websocket_continue(websocket, session_id)


@router.websocket("/delete/{session_id}")
async def websocket_delete(websocket: WebSocket, session_id: str):
    await ChatService.websocket_delete(websocket, session_id)