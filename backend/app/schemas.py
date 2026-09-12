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
    graph_edges: list[dict]
    quiz: list[dict]
    broken_cycles_count: int


class ErrorResponse(BaseModel):
    detail: str


class DocumentRecord(BaseModel):
    doc_id: str
    document_name: str
    chunks: list[dict]
    final_roadmap: Optional[dict] = None
    pdf_bytes: bytes  # lưu thẳng trong DB (không dùng file_path trên đĩa) để bền vững qua restart
