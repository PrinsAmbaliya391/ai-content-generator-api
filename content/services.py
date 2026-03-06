from google import genai
from google.genai.types import GenerateContentConfig
from core.config import GEMINI_KEY
from fastapi import HTTPException
from core.database import supabase
from typing import List
import asyncio
import time

client = genai.Client(api_key=GEMINI_KEY)


def count_words(text: str) -> int:
    return len(text.split())


def generate_large_content(topic, word_count, tone, language):
    outline_prompt = f"create a detailed 20-section technical outline for {topic}. return only the list of sub-topic titles."

    outline_response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=outline_prompt
    )

    sections = [
        s for s in outline_response.text.split("\n")
        if s.strip() and any(c.isalpha() for c in s)
    ]

    if not sections:
        raise Exception("outline generation failed")

    chunk_target = (word_count // len(sections)) + 50
    final_text = []
    previous_context = ""

    for i, section in enumerate(sections):
        prompt_topic = f"""
        topic: {topic}
        current focus: {section}
        context (continue exactly from here): "...{previous_context[-1000:]}"
        """

        part = generate_with_word_control(
            prompt_topic, chunk_target, tone, language
        )

        final_text.append(part)
        previous_context = part[-1000:]

    result = " ".join(final_text)

    while count_words(result) < word_count:
        extra = generate_content(
            f"continue the technical analysis of {topic}. focus on more data and case studies. context: {result[-1000:]}",
            500,
            tone,
            language
        )
        result += " " + extra

    words = result.split()
    final_result = " ".join(words[:word_count]).lower()

    return final_result


def generate_with_word_control(topic_prompt, word_count, tone, language):
    text = generate_content(topic_prompt, word_count, tone, language)

    if count_words(text) < (word_count * 0.8):
        expansion_prompt = f"expand this text to {word_count} words by adding technical data: {text}"
        text = generate_content(expansion_prompt, word_count, tone, language)

    return text


def generate_content(prompt_input, word_count, tone, language):
    prompt = f"""
role: professional academic writer.
task: {prompt_input}
tone: {tone}
language: {language}

rules:
- target: {word_count} words.
- style: everything must be lowercase. no capital letters.
- no headers. no titles. no ##. no section numbers.
- start immediately with the first word 'the' (if applicable).
- do not use introductory fluff or greetings.
"""

    generate_config = GenerateContentConfig(temperature=0.8)

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=prompt,
                config=generate_config
            )

            if response.text:
                return response.text.lower()

        except Exception:
            time.sleep(2)
            continue

    return ""


def refine_content_with_ai(model_response, user_change, disliked_part, word_count, tone, language):
    words = model_response.split()
    chunk_size = 1500
    refined_chunks = []

    for i in range(0, len(words), chunk_size):
        sub_text = " ".join(words[i:i + chunk_size])

        prompt = f"""
refine this part: {sub_text}

change to apply: {user_change}

remove: {disliked_part}

style: lowercase only. no headers. no capital letters.
"""

        refined_part = generate_content(
            prompt,
            len(sub_text.split()),
            tone,
            language
        )

        refined_chunks.append(refined_part)

    return " ".join(refined_chunks).lower()


def regenerate_content_with_ai(topic, word_count, tone, language):
    if word_count > 1500:
        return generate_large_content(topic, word_count, tone, language)
    else:
        return generate_content(
            f"write a new version of {topic}",
            word_count,
            tone,
            language
        )


def get_generation(generation_id, user_uuid):
    res = supabase.table("generations") \
        .select("*") \
        .eq("id", generation_id) \
        .eq("user_uuid", user_uuid) \
        .execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="not found")

    return res.data[0]


class ContentService:

    @staticmethod
    async def generate(req, user_uuid: str):

        user_res = await asyncio.to_thread(
            lambda: supabase.table("users")
            .select("is_verified")
            .eq("uuid", user_uuid)
            .execute()
        )

        if not user_res.data or not user_res.data[0]["is_verified"]:
            raise HTTPException(status_code=401, detail="verify email first")

        try:
            if req.word_count > 1500:
                result_text = await asyncio.to_thread(
                    generate_large_content,
                    req.topic,
                    req.word_count,
                    req.tone,
                    req.language
                )
            else:
                result_text = await asyncio.to_thread(
                    generate_content,
                    f"write about {req.topic}",
                    req.word_count,
                    req.tone,
                    req.language
                )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        await asyncio.to_thread(
            lambda: supabase.table("generations").insert({
                "user_uuid": user_uuid,
                "topic": req.topic,
                "content": [result_text],
                "status": ["generate"],
                "word_count": req.word_count,
                "tone": req.tone,
                "language": req.language
            }).execute()
        )

        return {"generated_text": result_text}

    @staticmethod
    async def update_content(req, user_uuid: str):

        current = await asyncio.to_thread(
            get_generation,
            req.generation_id,
            user_uuid
        )

        new_contents = current["content"] + [req.updated_text]
        new_status = current["status"] + ["update"]

        await asyncio.to_thread(
            lambda: supabase.table("generations")
            .update({
                "content": new_contents,
                "status": new_status
            })
            .eq("id", req.generation_id)
            .execute()
        )

        return {"status": "update"}

    @staticmethod
    async def refine_content(req, user_uuid):

        current = await asyncio.to_thread(
            get_generation,
            req.generation_id,
            user_uuid
        )

        refined_text = await asyncio.to_thread(
            refine_content_with_ai,
            current["content"][-1],
            req.user_change,
            req.disliked_part,
            current["word_count"],
            current["tone"],
            current["language"]
        )

        await asyncio.to_thread(
            lambda: supabase.table("generations")
            .update({
                "content": current["content"] + [refined_text],
                "status": current["status"] + ["refine"]
            })
            .eq("id", req.generation_id)
            .execute()
        )

        return {"updated_text": refined_text}

    @staticmethod
    async def regenerate_content(req, user_uuid):

        current = await asyncio.to_thread(
            get_generation,
            req.generation_id,
            user_uuid
        )

        new_text = await asyncio.to_thread(
            regenerate_content_with_ai,
            current["topic"],
            current["word_count"],
            current["tone"],
            current["language"]
        )

        await asyncio.to_thread(
            lambda: supabase.table("generations")
            .update({
                "content": current["content"] + [new_text],
                "status": current["status"] + ["regenerate"]
            })
            .eq("id", req.generation_id)
            .execute()
        )

        return {"updated_text": new_text}

    @staticmethod
    async def get_history(user_uuid: str):

        response = await asyncio.to_thread(
            lambda: supabase.table("generations")
            .select("*")
            .eq("user_uuid", user_uuid)
            .order("created_at", desc=True)
            .execute()
        )

        return {"history": response.data}

    @staticmethod
    async def delete(generation_id: int, user_uuid: str):

        await asyncio.to_thread(
            lambda: supabase.table("generations")
            .delete()
            .eq("id", generation_id)
            .eq("user_uuid", user_uuid)
            .execute()
        )

        return {"message": "deleted"}
    
content_service=ContentService()