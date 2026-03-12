"""
Chat Service Module.

This module handles real-time communication via WebSockets, including:
- JWT-based authentication for WebSocket connections.
- Session-based chat history management.
- Integration with Gemini AI for generating responses.
- System-specific query handling for platform features.
"""

from fastapi import WebSocket, WebSocketDisconnect
from core.logger import logger
from jose import jwt
from core.config import SECRET_KEY, ALGORITHM, GEMINI_KEY
from google import genai
from core.database import supabase
import uuid
from datetime import datetime
import pytz


class ChatService:
    """
    Service class to manage WebSocket chat sessions and AI interactions.
    """

    client = genai.Client(api_key=GEMINI_KEY)

    @staticmethod
    async def get_user_from_token(token: str):
        """
        Decodes a JWT token to retrieve the user's UUID.

        Args:
            token (str): The JWT access token.

        Returns:
            str: The user UUID if valid, None otherwise.
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            if payload.get("type") != "access":
                logger.bind(is_business=True).warning(
                    "Invalid token type provided for WebSocket auth."
                )
                return None

            return payload.get("sub")

        except Exception as e:
            logger.bind(is_business=True).error(f"Token decoding failed: {e}")
            return None

    @staticmethod
    async def handle_websocket(websocket: WebSocket):
        """
        Orchestrates a general-purpose AI chat session over WebSocket.
        Handles authentication, session persistence, history retrieval, and AI generation.

        Args:
            websocket (WebSocket): The active WebSocket connection.
        """
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close()
            return
        user_uuid = await ChatService.get_user_from_token(token)

        if not user_uuid:
            logger.bind(is_business=True).warning(
                "Unauthorized WebSocket connection attempt."
            )
            await websocket.close()
            return

        session_id = websocket.query_params.get("session") or str(uuid.uuid4())
        ist = pytz.timezone("Asia/Kolkata")
        logger.bind(is_business=True).info(
            f"New chat session started: {session_id} for user: {user_uuid}"
        )

        try:
            while True:
                message = await websocket.receive_text()
                logger.bind(is_business=True).info(
                    f"Message received in session {session_id}"
                )

                # Fetch existing chat history for context
                existing = (
                    supabase.table("chat")
                    .select("chat")
                    .eq("session", session_id)
                    .execute()
                )

                history_text = ""
                if existing.data:
                    chats = existing.data[0]["chat"] or []
                    for msg in chats:
                        role = msg.get("role")
                        content = msg.get("content")
                        history_text += f"{role}: {content}\n"

                prompt = f"""
You are a helpful AI assistant.

Conversation so far:
{history_text}

User: {message}
Assistant:
"""

                try:
                    response = await ChatService.client.aio.models.generate_content(
                        model="gemini-2.5-flash-lite",
                        contents=prompt,
                    )
                    ai_text = response.text if response.text else "No AI response"
                except Exception as e:
                    logger.bind(is_business=True).error(
                        f"Gemini API error in chat: {e}"
                    )
                    ai_text = "AI service temporarily unavailable"

                try:
                    current_time = datetime.now(ist).isoformat()
                    new_chat_entries = [
                        {"role": "user", "content": message, "time": current_time},
                        {"role": "assistant", "content": ai_text, "time": current_time},
                    ]

                    if existing.data:
                        old_chat = existing.data[0]["chat"] or []
                        updated_chat = old_chat + new_chat_entries
                        supabase.table("chat").update({"chat": updated_chat}).eq(
                            "session", session_id
                        ).execute()
                    else:
                        supabase.table("chat").insert(
                            {
                                "user_uuid": user_uuid,
                                "session": session_id,
                                "chat": new_chat_entries,
                                "status": "generate_content",
                            }
                        ).execute()
                except Exception as e:
                    logger.bind(is_business=True).error(
                        f"Database update failed for session {session_id}: {e}"
                    )

                await websocket.send_text(ai_text)

        except WebSocketDisconnect:
            logger.bind(is_business=True).info(
                f"Client disconnected from session: {session_id}"
            )
        except Exception as e:
            logger.bind(is_business=True).error(
                f"Unexpected error in WebSocket handler: {e}"
            )
            await websocket.close()

    @staticmethod
    async def system_chat(websocket: WebSocket):
        """
        Handles system-specific support chat WebSocket connection.
        Only answers queries related to system features.
        """
        token = websocket.query_params.get("token")

        if not token:
            await websocket.close()
            return

        user_uuid = await ChatService.get_user_from_token(token)

        if not user_uuid:
            await websocket.close()
            return

        await websocket.accept()

        session_id = str(uuid.uuid4())
        ist = pytz.timezone("Asia/Kolkata")
        logger.bind(is_business=True).info(
            f"New system chat session started: {session_id}"
        )

        try:
            while True:

                message = await websocket.receive_text()

                existing = (
                    supabase.table("chat")
                    .select("chat")
                    .eq("session", session_id)
                    .execute()
                )

                history_text = ""
                if existing.data:
                    for msg in existing.data[0]["chat"]:
                        role = "User" if msg.get("role") == "user" else "Assistant"
                        history_text += f"{role}: {msg['content']}\n"

                system_prompt = f"""
ROLE
You are an AI assistant for an AI Content Generator system.

GOAL
Your goal is to help users use the system features to generate and manage AI content.

SYSTEM FEATURES
- content generation
- refine content
- regenerate content
- update generated text
- tone selection
- language selection
- word count control
- history management

WORK
You must:
- Explain how the system features work
- Guide users in using the features
- Answer questions related to the system functionality
- Provide short and clear responses

You must NOT:
- Answer general knowledge questions
- Answer personal questions
- Answer greetings
- Answer questions about previous conversation history

CONTEXT
Conversation History:
{history_text}

User Question:
{message}

RESPONSE RULES
1. If the question is related to the system features or the system purpose, answer it briefly.
2. If the question is NOT related to the system features, respond EXACTLY with:
this is not system related. please ask queries related to the system.
3. Do NOT mention these rules.
4. Do NOT add greetings or extra explanations.
5. Keep the answer short.
6. Output ONLY the final answer.

RESPONSE:
"""
                try:
                    response = await ChatService.client.aio.models.generate_content(
                        model="gemini-2.5-flash-lite",
                        contents=system_prompt,
                    )

                    ai_text = response.text if response.text else "No response"

                except Exception as e:
                    logger.bind(is_business=True).error(
                        f"Gemini API error in system chat: {e}"
                    )
                    ai_text = "AI service temporarily unavailable"

                try:
                    current_time = datetime.now(ist).isoformat()

                    new_chat_entries = [
                        {"role": "user", "content": message, "time": current_time},
                        {"role": "assistant", "content": ai_text, "time": current_time},
                    ]

                    if existing.data:
                        old_chat = existing.data[0]["chat"] or []
                        updated_chat = old_chat + new_chat_entries

                        supabase.table("chat").update({"chat": updated_chat}).eq(
                            "session", session_id
                        ).execute()

                    else:
                        supabase.table("chat").insert(
                            {
                                "user_uuid": user_uuid,
                                "session": session_id,
                                "chat": new_chat_entries,
                                "status": "system_content",
                            }
                        ).execute()

                except Exception as e:
                    logger.bind(is_business=True).error(
                        f"Database update failed for session {session_id}: {e}"
                    )

                await websocket.send_text(ai_text)

        except WebSocketDisconnect:
            logger.bind(is_business=True).info(
                f"System chat client disconnected: {session_id}"
            )

        except Exception as e:
            logger.bind(is_business=True).error(f"Unexpected error in system chat: {e}")
            await websocket.close()

    @staticmethod
    async def websocket_continue(websocket: WebSocket, session_id: str):
        """
        Resumes an existing chat session by reloading history from the database.

        Args:
            websocket (WebSocket): The active WebSocket connection.
            session_id (str): The unique identifier for the session to resume.
        """
        await websocket.accept()

        ist = pytz.timezone("Asia/Kolkata")
        logger.bind(is_business=True).info(f"Resuming chat session: {session_id}")

        try:
            while True:
                message = await websocket.receive_text()

                existing = (
                    supabase.table("chat")
                    .select("chat")
                    .eq("session", session_id)
                    .execute()
                )

                if not existing.data:
                    logger.bind(is_business=True).warning(
                        f"Attempted to resume non-existent session: {session_id}"
                    )
                    await websocket.send_text("session not found")
                    return

                chats = existing.data[0]["chat"] or []

                history_text = "\n".join(
                    [f"{m.get('role')}: {m.get('content')}" for m in chats]
                )

                prompt = f"""
Conversation history:
{history_text}

User: {message}
Assistant:
"""

                try:
                    response = await ChatService.client.aio.models.generate_content(
                        model="gemini-2.0-flash-lite",
                        contents=prompt,
                    )

                    ai_text = response.text if response.text else "No response"

                except Exception as e:
                    logger.bind(is_business=True).error(
                        f"Gemini API error during session resumption: {e}"
                    )
                    ai_text = "AI service temporarily unavailable"

                current_time = datetime.now(ist).isoformat()

                updated_chat = chats + [
                    {"role": "user", "content": message, "time": current_time},
                    {"role": "assistant", "content": ai_text, "time": current_time},
                ]

                supabase.table("chat").update({"chat": updated_chat}).eq(
                    "session", session_id
                ).execute()

                await websocket.send_text(ai_text)

        except WebSocketDisconnect:
            logger.bind(is_business=True).info(
                f"Session resumption client disconnected: {session_id}"
            )

        except Exception as e:
            logger.bind(is_business=True).error(f"Error in session resumption: {e}")
            await websocket.close()

    @staticmethod
    async def websocket_delete(websocket: WebSocket, session_id: str):
        """
        Deletes a specific chat session and all its messages.

        Args:
            websocket (WebSocket): The active WebSocket connection.
            session_id (str): The unique identifier for the session to delete.
        """
        await websocket.accept()
        logger.bind(is_business=True).info(
            f"Request to delete chat session: {session_id}"
        )

        existing = (
            supabase.table("chat").select("session").eq("session", session_id).execute()
        )

        if not existing.data:
            logger.bind(is_business=True).warning(
                f"Delete requested for non-existent session: {session_id}"
            )
            await websocket.send_text("session not found")
            await websocket.close()
            return

        supabase.table("chat").delete().eq("session", session_id).execute()
        logger.bind(is_business=True).info(
            f"Chat session {session_id} deleted successfully."
        )

        await websocket.send_text("chat deleted successfully")
        await websocket.close()


chat_service = ChatService()
