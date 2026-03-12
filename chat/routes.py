"""
Chat WebSocket Routes Module.

This module defines the WebSocket endpoints for real-time AI chat
and system support query sessions.
"""

from fastapi import APIRouter, WebSocket, Query
from chat.services import chat_service as ChatService

router = APIRouter(prefix="/chat", tags=["Real-time Chat"])


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket, token: str = Query(None)):
    """
    Handles general AI chat interactions via WebSocket.

    Args:
        websocket (WebSocket): The active WebSocket connection.
        token (str, optional): JWT access token for authentication.
    """
    await websocket.accept()
    await ChatService.handle_websocket(websocket)


@router.websocket("/system")
async def websocket_system(websocket: WebSocket):
    """
    Handles system support queries via WebSocket.
    Constraints the AI to answer only platform-related functional questions.

    Args:
        websocket (WebSocket): The active WebSocket connection.
    """
    await ChatService.system_chat(websocket)


@router.websocket("/continue/{session_id}")
async def websocket_continue(websocket: WebSocket, session_id: str):
    """
    Resumes an existing chat session with full historical context.

    Args:
        websocket (WebSocket): The active WebSocket connection.
        session_id (str): The specific UUID of the session to resume.
    """
    await ChatService.websocket_continue(websocket, session_id)


@router.websocket("/delete/{session_id}")
async def websocket_delete(websocket: WebSocket, session_id: str):
    """
    Permanently deletes a chat session record from the database.

    Args:
        websocket (WebSocket): The active WebSocket connection.
        session_id (str): The UUID of the session to delete.
    """
    await ChatService.websocket_delete(websocket, session_id)
