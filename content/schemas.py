from pydantic import BaseModel


class ContentRequest(BaseModel):
    topic: str
    word_count: int
    tone: str
    language: str


class UpdateRequest(BaseModel):
    generation_id: int
    updated_text: str


class RefineRequest(BaseModel):
    generation_id: int
    user_change: str
    disliked_part: str


class RegenerateRequest(BaseModel):
    generation_id: int
