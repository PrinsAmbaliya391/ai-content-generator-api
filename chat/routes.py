"""
Chat WebSocket Routes Module.

This module defines the WebSocket endpoints for real-time AI chat
and system support query sessions.
"""

from fastapi import APIRouter, WebSocket
from chat.services import chat_service as ChatService

router = APIRouter(prefix="/chat", tags=["Real-time Chat"])


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """
    Handles general AI chat interactions via WebSocket.
    """
    await ChatService.handle_websocket(websocket)


@router.websocket("/system")
async def websocket_system(websocket: WebSocket):
    """
    Handles system support queries via WebSocket.
    """
    await ChatService.system_chat(websocket)


@router.websocket("/continue/{session_id}")
async def websocket_continue(websocket: WebSocket, session_id: str):
    """
    Resumes an existing chat session.
    """
    await ChatService.websocket_continue(websocket, session_id)


@router.websocket("/delete/{session_id}")
async def websocket_delete(websocket: WebSocket, session_id: str):
    """
    Deletes a specific chat session.
    """
    await ChatService.websocket_delete(websocket, session_id)
