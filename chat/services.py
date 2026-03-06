from fastapi import WebSocket, WebSocketDisconnect
from jose import jwt
from core.config import SECRET_KEY, ALGORITHM, GEMINI_KEY
from google import genai
from core.database import supabase
import uuid
from datetime import datetime
import pytz


class ChatService:
    client = genai.Client(api_key=GEMINI_KEY)

    @staticmethod
    async def get_user_from_token(token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            if payload.get("type") != "access":
                return None

            return payload.get("sub")

        except Exception:
            return None

    @staticmethod
    async def handle_websocket(websocket: WebSocket):
        auth_header = websocket.headers.get("authorization")

        if not auth_header:
            await websocket.accept()
            await websocket.close()
            return

        try:
            token = auth_header.split(" ")[1]
        except Exception:
            await websocket.accept()
            await websocket.close()
            return

        await websocket.accept()

        user_uuid = await ChatService.get_user_from_token(token)

        if not user_uuid:
            await websocket.close()
            return

        session_id = str(uuid.uuid4())
        ist = pytz.timezone("Asia/Kolkata")

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

                except Exception:
                    ai_text = "AI service temporarily unavailable"

                try:
                    current_time = datetime.now(ist).isoformat()

                    new_chat = [
                        {"role": "user", "content": message, "time": current_time},
                        {"role": "assistant", "content": ai_text, "time": current_time},
                    ]

                    if existing.data:
                        old_chat = existing.data[0]["chat"] or []
                        updated_chat = old_chat + new_chat

                        supabase.table("chat").update({"chat": updated_chat}).eq(
                            "session", session_id
                        ).execute()

                    else:
                        supabase.table("chat").insert(
                            {
                                "user_uuid": user_uuid,
                                "session": session_id,
                                "chat": new_chat,
                                "status": "generate_content",
                            }
                        ).execute()

                except Exception:
                    pass

                await websocket.send_text(ai_text)

        except WebSocketDisconnect:
            print("Client disconnected")

        except Exception:
            await websocket.close()

    @staticmethod
    async def system_chat(websocket: WebSocket):

        auth_header = websocket.headers.get("authorization")

        if not auth_header:
            await websocket.accept()
            await websocket.close()
            return

        try:
            token = auth_header.split(" ")[1]
        except Exception:
            await websocket.accept()
            await websocket.close()
            return

        await websocket.accept()

        user_uuid = await ChatService.get_user_from_token(token)

        if not user_uuid:
            await websocket.close()
            return

        session_id = str(uuid.uuid4())
        ist = pytz.timezone("Asia/Kolkata")

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
                        if msg.get("role") == "user":
                            history_text += f"User: {msg['content']}\n"
                        elif msg.get("role") == "assistant":
                            history_text += f"Assistant: {msg['content']}\n"

                system_prompt = f"""
You are an AI assistant for an AI Content Generator system.

You must ONLY answer questions related to the system features listed below.

System Features:
- content generation
- refine content
- regenerate content
- update generated text
- tone selection
- language selection
- word count control
- history management

Conversation History:
{history_text}

User Question:
{message}

Strict Rules:
1. Only answer questions directly related to the system features listed above.
2. If the question is about greetings, personal questions, general knowledge, previous questions, or anything outside the system features, respond EXACTLY with:
this is not system related. please ask queries related to the system.
3. Do NOT answer questions about conversation history such as "what was my previous question".
4. Keep responses short and direct.
5. Do NOT add greetings, explanations, or extra text.
6. Output ONLY the final answer.

Assistant Response:
"""
                try:
                    response = await ChatService.client.aio.models.generate_content(
                        model="gemini-2.5-flash-lite",
                        contents=system_prompt,
                    )

                    ai_text = response.text if response.text else "No response"

                except Exception:
                    ai_text = "AI service temporarily unavailable"

                try:
                    current_time = datetime.now(ist).isoformat()

                    new_chat = [
                        {"role": "user", "content": message, "time": current_time},
                        {"role": "assistant", "content": ai_text, "time": current_time},
                    ]

                    if existing.data:
                        old_chat = existing.data[0]["chat"] or []
                        updated_chat = old_chat + new_chat

                        supabase.table("chat").update({"chat": updated_chat}).eq(
                            "session", session_id
                        ).execute()

                    else:
                        supabase.table("chat").insert(
                            {
                                "user_uuid": user_uuid,
                                "session": session_id,
                                "chat": new_chat,
                                "status": "system_content",
                            }
                        ).execute()

                except Exception:
                    pass

                await websocket.send_text(ai_text)

        except WebSocketDisconnect:
            pass

        except Exception:
            await websocket.close()

    @staticmethod
    async def websocket_continue(websocket: WebSocket, session_id: str):

        await websocket.accept()

        ist = pytz.timezone("Asia/Kolkata")

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
                    await websocket.send_text("session not found")
                    return

                chats = existing.data[0]["chat"] or []

                history_text = ""
                for msg in chats:
                    role = msg.get("role")
                    content = msg.get("content")
                    history_text += f"{role}: {content}\n"

                prompt = f"""
    Conversation history:
    {history_text}

    User: {message}
    Assistant:
    """

                try:
                    response = await ChatService.client.aio.models.generate_content(
                        model="gemini-2.5-flash-lite",
                        contents=prompt,
                    )

                    ai_text = response.text if response.text else "No response"

                except Exception:
                    ai_text = "AI service temporarily unavailable"

                current_time = datetime.now(ist).isoformat()

                new_chat = [
                    {"role": "user", "content": message, "time": current_time},
                    {"role": "assistant", "content": ai_text, "time": current_time},
                ]

                updated_chat = chats + new_chat

                supabase.table("chat").update({"chat": updated_chat}).eq(
                    "session", session_id
                ).execute()

                await websocket.send_text(ai_text)

        except WebSocketDisconnect:
            pass

    @staticmethod
    async def websocket_delete(websocket: WebSocket, session_id: str):

        await websocket.accept()

        existing = (
            supabase.table("chat").select("session").eq("session", session_id).execute()
        )

        if not existing.data:
            await websocket.send_text("session not found")
            await websocket.close()
            return

        supabase.table("chat").delete().eq("session", session_id).execute()

        await websocket.send_text("chat deleted successfully")
        await websocket.close()


chat_service = ChatService()
