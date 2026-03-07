from google import genai
from google.genai.types import GenerateContentConfig
from core.config import GEMINI_KEY
from fastapi import HTTPException
from core.database import supabase
from typing import List
import asyncio
import time
import fitz 
import docx 
import io
from fastapi import UploadFile
from typing import Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma


client = genai.Client(api_key=GEMINI_KEY)

persist_directory = "chroma_db"

def create_vector_store_from_text(text):

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    docs = text_splitter.create_documents([text])

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GEMINI_KEY")
    )

    vectordb = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=persist_directory
    )

    vectordb.persist()

    return vectordb

def search_vector(query):

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GEMINI_KEY")
    )

    vectordb = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )

    docs = vectordb.similarity_search(query, k=4)

    context = "\n".join([doc.page_content for doc in docs])

    return context

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
        Topic/Goal: {topic} (Use provided Reference Documents if applicable)
        Current focus: {section}
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
    is_rag = "<document>" in prompt_input
    
    persona = "You are a helpful assistant." if is_rag else "you are a professional academic writer."
    
    constraint = "Use ONLY the provided document to answer. Do not add outside knowledge." if is_rag else "expand the explanation logically."

    prompt = f"""
{persona}

task:
{prompt_input}

write a detailed explanation with examples and context.
the response must be close to the target word count.

rules:
{constraint}
- strictly rely on the document when answering
- do not invent information
- if the document does not contain the answer say: information not found in document

writing settings:
tone: {tone}
language: {language}
target words: {word_count}

style rules:
- everything must be lowercase
- no headers
- no titles
- start directly with the answer
"""

    generate_config = GenerateContentConfig(temperature=0.7)

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


def extract_text_from_file(file: UploadFile):

    file.file.seek(0)

    content = ""
    ext = file.filename.split('.')[-1].lower()

    data = file.file.read()

    if ext == "txt":
        content = data.decode("utf-8", errors="ignore")

    elif ext == "pdf":
        doc = fitz.open(stream=data, filetype="pdf")
        for page in doc:
            content += page.get_text("text")

    elif ext in ["docx", "doc"]:
        document = docx.Document(io.BytesIO(data))
        for para in document.paragraphs:
            content += para.text + "\n"

    return content


class ContentService:

    @staticmethod
    async def generate(req, user_uuid: str, file: Optional[UploadFile] = None):
        
        user_res = await asyncio.to_thread(
            lambda: supabase.table("users")
            .select("is_verified")
            .eq("uuid", user_uuid)
            .execute()
        )

        if not user_res.data or not user_res.data[0]["is_verified"]:
            raise HTTPException(status_code=401, detail="verify email first")

        doc_context = ""

        if file:

            doc_context = await asyncio.to_thread(extract_text_from_file, file)

            await asyncio.to_thread(create_vector_store_from_text, doc_context)

            rag_context = await asyncio.to_thread(search_vector, req.topic)

            task_input = f"""
        answer the question using ONLY the document.

        <context>
        {rag_context}
        </context>

        <question>
        {req.topic}
        </question>

        rules:
        - only use document information
        - do not use outside knowledge
        - if answer not found say: information not found in document
        """

        else:

            task_input = f"""
        You are a professional academic writer.

        QUESTION:
        {req.topic}

        Write a professional explanation.
        """

        try:

            if req.word_count > 1500 and not doc_context:

                result_text = await asyncio.to_thread(
                    generate_large_content,
                    task_input,
                    req.word_count,
                    req.tone,
                    req.language
                )

            else:

                result_text = await asyncio.to_thread(
                    generate_with_word_control,
                    task_input,
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