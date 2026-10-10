from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    pages: int
    chunks: int
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
