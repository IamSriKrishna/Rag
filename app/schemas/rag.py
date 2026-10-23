from pydantic import BaseModel, Field


class RAGRequest(BaseModel):
    document_id: int | None = None
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None


class SourceResponse(BaseModel):
    filename: str
    page: int | None = None
    excerpt: str


class RAGResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
    conversation_id: int | None = None
    cached: bool = False
