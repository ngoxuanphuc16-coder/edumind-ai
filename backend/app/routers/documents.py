import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.dependencies import get_document_store, get_llm_client, get_vector_store
from app.graph.pipeline import build_graph
from app.graph.state import make_initial_state
from app.schemas import DocumentRecord, ProcessResponse, UploadResponse
from app.services.document_parser import DocumentParseError, parse_pdf_to_chunks
from app.services.document_store import InMemoryDocumentStore
from app.services.llm_client import LLMClient
from app.services.vector_store import VectorStore

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile,
    store: InMemoryDocumentStore = Depends(get_document_store),
    llm: LLMClient = Depends(get_llm_client),
    vector_store: VectorStore = Depends(get_vector_store),
):
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file PDF ở giai đoạn này.")

    doc_id = str(uuid.uuid4())
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{doc_id}.pdf"

    content = await file.read()
    file_path.write_bytes(content)

    try:
        chunks = parse_pdf_to_chunks(str(file_path), doc_id=doc_id, document_name=file.filename)
    except DocumentParseError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Embed + lưu vào Qdrant ngay ở bước upload (không đợi /process) -- để tính năng
    # Q&A retrieval (mục 2, implementation_plan.md) dùng được độc lập với luồng
    # sinh roadmap, kể cả khi roadmap chưa/không được tạo.
    embeddings = llm.embed([c["text"] for c in chunks])
    vector_store.upsert_chunks(chunks, embeddings)

    store.save(DocumentRecord(
        doc_id=doc_id, document_name=file.filename, file_path=str(file_path), chunks=chunks,
    ))

    return UploadResponse(doc_id=doc_id, document_name=file.filename, num_chunks=len(chunks))


@router.post("/{doc_id}/process", response_model=ProcessResponse)
def process_document(
    doc_id: str,
    store: InMemoryDocumentStore = Depends(get_document_store),
    llm: LLMClient = Depends(get_llm_client),
):
    record = store.get(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu, hãy /upload trước.")

    graph = build_graph(llm, settings)
    initial_state = make_initial_state(
        documents=[{"doc_id": doc_id, "name": record.document_name}],
        chunks=record.chunks,
        kg_triplets=[],
    )
    result = graph.invoke(initial_state)

    record.final_roadmap = result["final_roadmap"]
    store.save(record)

    return ProcessResponse(
        doc_id=doc_id,
        verification_status=result["final_roadmap"]["verification_status"],
        retry_count=result["final_roadmap"]["retry_count"],
        roadmap=result["final_roadmap"]["roadmap"],
        dag_order=result["final_roadmap"]["dag_order"],
        graph_edges=result["final_roadmap"]["graph_edges"],
        quiz=result["final_roadmap"]["quiz"],
        broken_cycles_count=len(result.get("broken_cycles", [])),
    )


@router.get("/{doc_id}/file")
def get_document_file(doc_id: str, store: InMemoryDocumentStore = Depends(get_document_store)):
    record = store.get(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    return FileResponse(record.file_path, media_type="application/pdf", filename=record.document_name)


@router.get("/{doc_id}/roadmap")
def get_roadmap(doc_id: str, store: InMemoryDocumentStore = Depends(get_document_store)):
    record = store.get(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    if record.final_roadmap is None:
        raise HTTPException(status_code=409, detail="Tài liệu chưa được xử lý, gọi /process trước.")
    return record.final_roadmap
