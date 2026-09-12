"""Q&A service -- luồng dữ liệu thứ 2 trong implementation_plan.md (mục 2),
tách biệt khỏi ingestion pipeline (app/graph/).

Không dùng LangGraph StateGraph ở đây: đây là 1 lượt retrieve -> generate ->
verify tuyến tính, không có nhánh rẽ/loop nhiều bước như vòng lặp fact-check
của roadmap, nên không cần thêm độ phức tạp của StateGraph.

Chỉ retry TỐI ĐA 1 LẦN (khác với MAX_RETRIES=3 của ingestion) vì đây là
tương tác trực tiếp (chat) -- sinh viên chờ 3 lượt kiểm chứng cho một câu hỏi
đơn giản là quá chậm. Nếu vẫn không đạt sau 1 lần sửa, trả câu trả lời kèm
`confidence: "low"` thay vì tiếp tục loop.
"""

from typing import List

from app.config import Settings
from app.graph.state import Chunk
from app.graph.verification import verify_citations_against_chunks
from app.services.hybrid_retrieval import hybrid_search
from app.services.llm_client import LLMClient
from app.services.vector_store import VectorStore


def answer_question(
    question: str,
    doc_id: str,
    all_chunks: List[Chunk],
    llm: LLMClient,
    vector_store: VectorStore,
    settings: Settings,
    top_k: int = 5,
) -> dict:
    # Qdrant embedded chạy trên ổ đĩa tạm của Render, mất khi service restart --
    # dù chunks đã bền vững trong DB (Turso). Phát hiện qua count_for_doc == 0 và
    # tự embed lại trước khi search, thay vì trả lời "không tìm thấy" sai lệch.
    if all_chunks and vector_store.count_for_doc(doc_id) == 0:
        embeddings = llm.embed([c["text"] for c in all_chunks])
        vector_store.upsert_chunks(all_chunks, embeddings)

    retrieved = hybrid_search(question, doc_id, all_chunks, llm, vector_store, top_k=top_k)

    if not retrieved:
        return {
            "answer": "Không tìm thấy đoạn nào trong tài liệu liên quan đến câu hỏi này.",
            "citations": [], "confidence": "low", "retrieved_chunks": [],
        }

    feedback = ""
    for attempt in range(2):  # tối đa 1 lần sửa (khác ingestion loop, xem docstring)
        result = llm.answer_question(question, retrieved, feedback=feedback)
        hard_check = verify_citations_against_chunks(
            [{"node_id": "qa", "citations": result.get("citations", [])}],
            retrieved,
            settings.citation_match_threshold,
        )
        is_grounded = hard_check["coverage_ratio"] >= settings.faithfulness_threshold and not hard_check["unmatched_citations"]
        if is_grounded:
            confidence = "high"
            break
        feedback = f"Citation không khớp đoạn trích gốc: {hard_check['unmatched_citations']}"
        confidence = "low"

    return {
        "answer": result.get("answer", ""),
        "citations": result.get("citations", []),
        "confidence": confidence,
        "retrieved_chunks": [
            {"chunk_id": c["chunk_id"], "page_number": c["page_number"], "document_name": c["document_name"]}
            for c in retrieved
        ],
    }
