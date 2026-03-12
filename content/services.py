"""
Content Service Module.

This module provides functionality for AI content generation, specifically:
- RAG (Retrieval Augmented Generation) using Gemini embeddings and ChromaDB.
- Large-scale technical content generation with outline-based expansion.
- Tone detection and dataset curation for model training.
- File text extraction (PDF, DOCX, TXT).
"""

from google import genai
from google.genai.types import (
    GenerateContentConfig,
    SafetySetting,
    HarmCategory,
    HarmBlockThreshold,
)
import csv
from core.config import GEMINI_KEY
from core.logger import logger
from fastapi import HTTPException
from core.database import supabase
from typing import List, Optional
import asyncio
import time
import fitz  # PyMuPDF
import docx
import io
import os
from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
import joblib
import re
import __main__
from sklearn.base import BaseEstimator, TransformerMixin


class TextPreprocessor(BaseEstimator, TransformerMixin):
    """
    Custom Scikit-learn transformer for text cleaning.
    Used by the pickled tone detection model.
    """

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        """
        Cleans input text: lowercase, remove punctuation, strip whitespace.
        """
        processed_data = []
        for text in X:
            text = text.lower()
            text = re.sub(r"[^a-z\s]", "", text)
            text = re.sub(r"\s+", " ", text).strip()
            processed_data.append(text)
        return processed_data


# Inject the preprocessor into __main__ as required by the pickled model
setattr(__main__, "TextPreprocessor", TextPreprocessor)

# Path configuration for ML assets
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "ml_model", "tone_model.pkl")

# Load the tone detection model
try:
    tone_model = joblib.load(MODEL_PATH)
except Exception as e:
    logger.bind(is_business=True).error(
        f"Failed to load tone model from {MODEL_PATH}: {e}"
    )
    tone_model = None

client = genai.Client(api_key=GEMINI_KEY)


def detect_tone(text: str) -> str:
    """
    Predicts the tone of the given text using the ML model.

    Args:
        text (str): The text to analyze.

    Returns:
        str: The detected tone label.
    """
    if not tone_model:
        return "neutral"
    prediction = tone_model.predict([text])
    return prediction[0]


def append_to_dataset(tone: str, content: str):
    """
    Appends a text sample and its tone label to the training dataset CSV.

    Args:
        tone (str): The label for the text.
        content (str): The text content.
    """
    dataset_path = os.path.join(BASE_DIR, "ml_model", "tone_dataset.csv")
    try:
        with open(dataset_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([tone, content])
    except Exception as e:
        logger.bind(is_business=True).error(f"Error appending to dataset: {e}")


# LangChain Google Embedding Configuration
embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001", google_api_key=GEMINI_KEY
)


def search_vector_from_text(text: str, query: str) -> str:
    """
    Performs a similarity search on a text segment using RAG.

    Args:
        text (str): The full document text to index.
        query (str): The search query.

    Returns:
        str: Concatenated relevant chunks for context.
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.create_documents([text])

    try:
        vectordb = Chroma.from_documents(
            documents=docs, embedding=embeddings, collection_name="temp_doc"
        )
        results = vectordb.similarity_search(query, k=4)
        return "\n".join([doc.page_content for doc in results])
    except Exception as e:
        logger.bind(is_business=True).error(f"RAG Error: {e}")
        raise HTTPException(status_code=500, detail="Vector search service unavailable")


async def simple_yes_no_check(prompt: str) -> str:
    """
    Sends a simple prompt to Gemini and expects a YES/NO response.

    Args:
        prompt (str): The verification prompt.

    Returns:
        str: Cleaned response text (usually YES or NO).
    """
    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-3.1-flash-lite-preview",
        contents=prompt,
    )
    return (response.text or "").strip().upper()


def count_words(text: str) -> int:
    """Helper to count words in a string."""
    return len(text.split())


async def generate_large_content(
    topic: str, word_count: int, tone: str, language: str
) -> str:
    """
    Generates long-form content by first creating an outline and then building sections.

    Args:
        topic (str): The main topic or prompt.
        word_count (int): Target word count.
        tone (str): Desired tone.
        language (str): Target language.

    Returns:
        str: The complete long-form text.
    """
    outline_prompt = f"create a detailed 20-section technical outline for {topic}. return only the list of sub-topic titles."

    outline_response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-3.1-flash-lite-preview",
        contents=outline_prompt,
    )

    sections = [
        s
        for s in outline_response.text.split("\n")
        if s.strip() and any(c.isalpha() for c in s)
    ]

    if not sections:
        raise Exception("Outline generation failed")

    chunk_target = (word_count // len(sections)) + 50
    final_text = []

    for section in sections:
        prompt_topic = f"Topic: {topic}\nFocus: {section}"
        part = await generate_with_word_control(
            prompt_topic, chunk_target, tone, language
        )
        final_text.append(part)

    result = " ".join(final_text)

    # Final word count padding if necessary
    while count_words(result) < word_count:
        extra = await generate_content(
            f"continue the technical analysis of {topic}. context: {result[-1000:]}",
            500,
            tone,
            language,
        )
        if not extra:
            break
        result += " " + extra

    words = result.split()
    return " ".join(words[:word_count])


async def generate_with_word_control(
    topic_prompt: str, word_count: int, tone: str, language: str
) -> str:
    """
    Wraps generation to ensure target length is met via expansion if needed.
    """
    text = await generate_content(topic_prompt, word_count, tone, language)

    if count_words(text) < (word_count * 0.8):
        expansion_prompt = f"expand this text to {word_count} words: {text}"
        text = await generate_content(expansion_prompt, word_count, tone, language)

    return text


async def generate_content(
    prompt_input: str, word_count: int, tone: str, language: str
) -> str:
    """
    Base low-level generation call with strict tone and style rules.
    """
    is_rag = "<document>" in prompt_input
    persona = (
        "You are a professional assistant."
        if is_rag
        else "You are a professional academic writer."
    )

    prompt = f"""
ROLE:
{persona}

GOAL:
Generate a high-quality response to the task while strictly following the required tone, language, and document-based knowledge constraints.

TASK:
{prompt_input}

WORK:
1. Carefully read the provided document and task.
2. Extract only the information that directly answers the question.
3. Structure the response clearly in paragraphs.
4. Maintain the requested tone throughout the entire response.
5. Ensure the response length is close to the target word count.

TONE INSTRUCTION (CRITICAL):
The entire response must be written strictly in a "{tone}" tone.
Every sentence must clearly reflect the "{tone}" tone.

TONE RULES:
- Do not mix tones.
- Do not switch tone anywhere in the response.
- Do not soften the tone.
- Do not add neutral sentences.
- Every paragraph must maintain the same tone.
- Every sentence must reflect the "{tone}" tone.

CONTENT RULES (CRITICAL):
- The document is the ONLY source of truth.
- Do not use external knowledge.
- Never guess or invent information.
- If the answer is not explicitly stated in the document, respond ONLY with:
i can only answer questions based on the provided document.

WRITING SETTINGS:
- Language: {language}
- Target length: approximately {word_count} words.

STYLE RULES:
- Use natural sentence casing.
- Do not include headers or titles.
- Start directly with the answer.
- Write only in paragraph format.

VALIDATION BEFORE RESPONDING:
Confirm internally that:
1. The tone is strictly "{tone}".
2. The tone does not change anywhere.
3. All information comes from the document only.

OUTPUT:
Return only the final generated answer.
Do not include explanations, notes, or metadata.
"""
    generate_config = GenerateContentConfig(
        temperature=0.6,
        safety_settings=[
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH,
            )
        ],
    )

    for attempt in range(3):
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-3.1-flash-lite-preview",
                contents=prompt,
                config=generate_config,
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            logger.bind(is_business=True).error(f"Attempt {attempt} failed: {e}")
            await asyncio.sleep(1)

    return ""


async def refine_content_with_ai(
    model_response: str,
    user_change: str,
    disliked_part: str,
    tone: str,
    language: str,
) -> str:

    target_words = count_words(model_response)

    prompt = f"""
ROLE:
You are a professional AI content editor and writing specialist.

GOAL:
Refine and improve the provided text according to the user's request while preserving the original topic and structure.

INPUT:
Current Text:
{model_response}

User Request:
{user_change}

Disliked Part:
{disliked_part}

WORK:
1. Carefully analyze the current text.
2. Identify the section the user disliked.
3. Apply the requested change to improve that section.
4. Enhance clarity, readability, and impact where necessary.
5. Ensure the text remains coherent and logically structured.

RULES:
- Do not change the main topic.
- Modify only the relevant parts of the text.
- Keep the rest of the content consistent.
- Maintain the tone: {tone}.
- Maintain the language: {language}.
- Keep approximately the same word count as the original text.
- Do not remove important information.

OUTPUT:
Return the FULL refined text only.
Do not explain the changes.
Do not add comments or notes.
"""

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-3.1-flash-lite-preview",
        contents=prompt,
    )

    return response.text


async def regenerate_content_with_ai(
    question: str,
    document_context: str,
    previous_answer: str,
    word_count: int,
    tone: str,
    language: str,
) -> str:

    prompt = f"""
<document>
{document_context}
</document>

<question>
{question}
</question>

<previous_answer>
{previous_answer}
</previous_answer>

task:
generate a COMPLETELY NEW answer using the document.

strict rules:
- the previous answer is shown only as a reference
- DO NOT repeat sentences
- DO NOT reuse phrasing
- DO NOT follow the same structure
- DO NOT paraphrase the previous answer

writing requirements:
- explain the information in a different way
- change the explanation order
- use different sentence structures
- focus on different parts of the document if possible

knowledge rules:
- use ONLY the document
- never add external knowledge
- if the answer is not explicitly in the document respond EXACTLY with:
i can only answer questions based on the provided document.

target words: {word_count}
language: {language}
"""

    return await generate_content(prompt, word_count, tone, language)


def get_generation(generations_uuid: str, user_uuid: str) -> dict:
    """
    Fetches a generation record and its associated contents from Supabase.
    """
    # Fetch metadata
    gen_res = (
        supabase.table("generations")
        .select("*")
        .eq("generations_uuid", generations_uuid)
        .eq("user_uuid", user_uuid)
        .execute()
    )
    if not gen_res.data:
        raise HTTPException(status_code=404, detail="Generation not found")

    generation = gen_res.data[0]
    gen_uuid = generation["generations_uuid"]

    # Ensure document context exists
    generation["document_context"] = generation.get("document_context", "")

    # Fetch contents
    content_res = (
        supabase.table("generation_contents")
        .select("*")
        .eq("generations_uuid", gen_uuid)
        .order("created_at", desc=False)
        .execute()
    )

    # Map into a structure compatible with existing service logic
    generation["content"] = [c["content"] for c in content_res.data]
    generation["status"] = [c["status"] for c in content_res.data]

    return generation


def extract_text_from_file(file: UploadFile) -> str:
    """
    Extracts text content from various file formats.
    """
    file.file.seek(0)
    ext = file.filename.split(".")[-1].lower()
    data = file.file.read()

    if ext == "txt":
        return data.decode("utf-8", errors="ignore")
    elif ext == "pdf":
        doc = fitz.open(stream=data, filetype="pdf")
        return "".join([page.get_text("text") for page in doc])
    elif ext == "docx":
        document = docx.Document(io.BytesIO(data))
        return "\n".join([para.text for para in document.paragraphs])
    return ""


class ContentService:
    """
    High-level orchestration service for AI content operations.
    """

    @staticmethod
    async def generate(req, user_uuid: str, file: Optional[UploadFile] = None):
        """
        Main entry point for generating new content from a document (RAG).
        """
        # User verification
        user_res = (
            supabase.table("users")
            .select("is_verified")
            .eq("uuid", user_uuid)
            .execute()
        )
        if not user_res.data or not user_res.data[0]["is_verified"]:
            raise HTTPException(status_code=401, detail="Verify email first")

        if not file:
            raise HTTPException(status_code=400, detail="Document required.")

        # RAG context creation
        doc_context = await asyncio.to_thread(extract_text_from_file, file)
        rag_context = await asyncio.to_thread(
            search_vector_from_text, doc_context, req.topic
        )

        check_prompt = f"""
ROLE:
You are a strict document verification assistant.

GOAL:
Determine whether the document contains enough information to answer the question.

DOCUMENT:
{rag_context}

QUESTION:
{req.topic}

WORK:
1. Carefully read the document.
2. Check if the document explicitly contains the information needed to answer the question.
3. Do not infer or assume missing information.

RULES:
- Only check information that is explicitly present in the document.
- Do not use external knowledge.
- Do not guess.
- If the answer is clearly present in the document, respond with YES.
- If the answer is missing or unclear, respond with NO.

OUTPUT:
Respond with ONLY one word:
YES
or
NO
"""
        check_response = await simple_yes_no_check(check_prompt)

        if "YES" not in check_response.upper():
            raise HTTPException(
                status_code=404, detail="Document context insufficient."
            )

        if not rag_context.strip():
            raise HTTPException(
                status_code=404, detail="No relevant information found in the document."
            )

        task_input = (
            f"<document>{rag_context}</document>\n<question>{req.topic}</question>"
        )

        try:
            if req.word_count > 1500:
                result_text = await generate_large_content(
                    task_input, req.word_count, req.tone, req.language
                )
            else:
                result_text = await generate_with_word_control(
                    task_input, req.word_count, req.tone, req.language
                )
        except Exception as e:
            logger.bind(is_business=True).error(f"AI Generation Failed: {e}")
            raise HTTPException(status_code=500, detail="AI Service Error")

        # Tone analysis and CSV curation
        model_tone = await asyncio.to_thread(detect_tone, result_text)
        if model_tone.lower() != req.tone.lower():
            # Run in background so user doesn't wait for dataset curation
            asyncio.create_task(
                ContentService._curate_dataset(task_input, req, model_tone)
            )
        # Database storage
        # 1. Insert metadata into 'generations'
        db_data = {
            "user_uuid": user_uuid,
            "topic": req.topic,
            "word_count": req.word_count,
            "tone": req.tone,
            "language": req.language,
            "document_context": rag_context,
        }
        insert_gen_res = await asyncio.to_thread(
            lambda: supabase.table("generations").insert(db_data).execute()
        )

        if not insert_gen_res.data:
            raise HTTPException(
                status_code=500, detail="Failed to save generation metadata"
            )

        new_gen = insert_gen_res.data[0]
        gen_uuid = new_gen["generations_uuid"]

        # 2. Insert actual content into 'generation_contents'
        content_data = {
            "generations_uuid": gen_uuid,
            "content": result_text,
            "status": "generate",
        }

        await asyncio.to_thread(
            lambda: supabase.table("generation_contents").insert(content_data).execute()
        )

        return {
            "id": new_gen["id"],
            "generations_uuid": new_gen["generations_uuid"],
            "generated_text": result_text,
            "user_tone": req.tone,
            "model_tone": model_tone,
        }

    @staticmethod
    async def _curate_dataset(task_input, req, model_tone):
        """Helper to handle dataset appending without blocking the main response."""
        dataset_version = await generate_with_word_control(
            task_input, req.word_count, model_tone, req.language
        )
        if dataset_version:
            await asyncio.to_thread(append_to_dataset, model_tone, dataset_version)

    @staticmethod
    async def update_content(req, user_uuid: str):
        """Appends manual edits as a new record in generation_contents."""
        current = await asyncio.to_thread(
            get_generation, req.generations_uuid, user_uuid
        )

        content_data = {
            "generations_uuid": current["generations_uuid"],
            "content": req.updated_text,
            "status": "update",
        }

        await asyncio.to_thread(
            lambda: supabase.table("generation_contents").insert(content_data).execute()
        )
        return {"status": "update"}

    @staticmethod
    async def refine_content(req, user_uuid: str):
        """Refines existing content and saves as a new record in generation_contents."""
        current = await asyncio.to_thread(
            get_generation, req.generations_uuid, user_uuid
        )
        refined_text = await refine_content_with_ai(
            current["content"][-1],
            req.user_change,
            req.disliked_part,
            current["tone"],
            current["language"],
        )

        content_data = {
            "generations_uuid": current["generations_uuid"],
            "content": refined_text,
            "status": "refine",
        }

        await asyncio.to_thread(
            lambda: supabase.table("generation_contents").insert(content_data).execute()
        )
        return {"updated_text": refined_text}

    @staticmethod
    async def regenerate_content(req, user_uuid: str):
        """Creates a completely new AI version and saves to generation_contents."""
        current = await asyncio.to_thread(
            get_generation, req.generations_uuid, user_uuid
        )
        if not current["content"]:
            raise HTTPException(
                status_code=400, detail="No previous content available to regenerate."
            )

        previous_answer = current["content"][-1]

        doc_context = current.get("document_context")

        if not doc_context:
            raise HTTPException(
                status_code=400,
                detail="Document context missing. Cannot regenerate answer.",
            )

        new_text = await regenerate_content_with_ai(
            current["topic"],
            doc_context,
            previous_answer,
            current["word_count"],
            current["tone"],
            current["language"],
        )

        content_data = {
            "generations_uuid": current["generations_uuid"],
            "content": new_text,
            "status": "regenerate",
        }

        await asyncio.to_thread(
            lambda: supabase.table("generation_contents").insert(content_data).execute()
        )
        return {"updated_text": new_text}

    @staticmethod
    async def get_history(user_uuid: str):
        """Retrieves generation history for a user including all content versions."""
        # 1. Fetch generations
        gen_res = await asyncio.to_thread(
            lambda: supabase.table("generations")
            .select("*, generation_contents(*)")
            .eq("user_uuid", user_uuid)
            .order("created_at", desc=True)
            .execute()
        )

        # Format the output to match the previous list-based structure if needed
        history = []
        for g in gen_res.data:
            # Sort contents by created_at to maintain correct history order
            contents = sorted(
                g.get("generation_contents", []), key=lambda x: x["created_at"]
            )
            g["content"] = [c["content"] for c in contents]
            g["status"] = [c["status"] for c in contents]
            # Remove the nested object to keep it clean
            if "generation_contents" in g:
                del g["generation_contents"]
            history.append(g)

        return {"history": history}

    @staticmethod
    async def delete(generations_uuid: str, user_uuid: str):
        """Deletes a generation from history."""
        await asyncio.to_thread(
            lambda: supabase.table("generations")
            .delete()
            .eq("generations_uuid", generations_uuid)
            .eq("user_uuid", user_uuid)
            .execute()
        )
        return {"message": "deleted"}


content_service = ContentService()
