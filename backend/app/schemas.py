from typing import Literal, Optional

from pydantic import BaseModel


class UploadResponse(BaseModel):
    doc_id: str
    document_name: str
    num_chunks: int


class ProcessResponse(BaseModel):
    doc_id: str
    verification_status: Literal["approved", "approved_with_warning"]
    retry_count: int
    roadmap: list[dict]
    dag_order: list[str]
    quiz: list[dict]
    broken_cycles_count: int


class ErrorResponse(BaseModel):
    detail: str


class DocumentRecord(BaseModel):
    doc_id: str
    document_name: str
    file_path: str
    chunks: list[dict]
    final_roadmap: Optional[dict] = None
