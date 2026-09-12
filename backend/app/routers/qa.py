from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.dependencies import get_document_store, get_llm_client, get_vector_store
from app.services.document_store import SqlDocumentStore
from app.services.llm_client import LLMClient
from app.services.qa_service import answer_question
from app.services.vector_store import VectorStore

router = APIRouter(prefix="/documents", tags=["qa"])


class AskRequest(BaseModel):
    question: str


@router.post("/{doc_id}/ask")
def ask_question(
    doc_id: str,
    body: AskRequest,
    store: SqlDocumentStore = Depends(get_document_store),
    llm: LLMClient = Depends(get_llm_client),
    vector_store: VectorStore = Depends(get_vector_store),
):
    record = store.get(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu, hãy /upload trước.")
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")

    return answer_question(
        question=body.question,
        doc_id=doc_id,
        all_chunks=record.chunks,
        llm=llm,
        vector_store=vector_store,
        settings=settings,
    )
