<<<<<<< HEAD
"""
Chat WebSocket Routes Module.

This module defines the WebSocket endpoints for real-time AI chat
and system support query sessions.
"""

from fastapi import APIRouter, WebSocket
from chat.services import chat_service as ChatService

router = APIRouter(prefix="/chat", tags=["Real-time Chat"])
=======
from fastapi import APIRouter, WebSocket
from chat.services import chat_service as ChatService

router = APIRouter(prefix="/chat")
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
<<<<<<< HEAD
    """
    Handles general AI chat interactions via WebSocket.
    """
=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    await ChatService.handle_websocket(websocket)


@router.websocket("/system")
async def websocket_system(websocket: WebSocket):
<<<<<<< HEAD
    """
    Handles system support queries via WebSocket.
    """
=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    await ChatService.system_chat(websocket)


@router.websocket("/continue/{session_id}")
async def websocket_continue(websocket: WebSocket, session_id: str):
<<<<<<< HEAD
    """
    Resumes an existing chat session.
    """
=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    await ChatService.websocket_continue(websocket, session_id)


@router.websocket("/delete/{session_id}")
async def websocket_delete(websocket: WebSocket, session_id: str):
<<<<<<< HEAD
    """
    Deletes a specific chat session.
    """
    await ChatService.websocket_delete(websocket, session_id)
=======
    await ChatService.websocket_delete(websocket, session_id)
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
