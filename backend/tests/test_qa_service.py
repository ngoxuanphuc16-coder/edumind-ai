import shutil
import tempfile

from app.config import Settings
from app.services.llm_client import MockLLMClient
from app.services.qa_service import answer_question
from app.services.vector_store import VectorStore


def test_answer_question_returns_grounded_result():
    tmp = tempfile.mkdtemp()
    try:
        settings = Settings(qdrant_path=tmp, qdrant_vector_size=8)
        vector_store = VectorStore(path=tmp, url=None, collection="test_qa", vector_size=8)
        llm = MockLLMClient(embedding_dim=8)

        chunks = [{"chunk_id": "c1", "doc_id": "d1", "document_name": "doc.pdf", "page_number": 1,
                   "text": "QuickSort chon mot phan tu lam chot."}]
        vector_store.upsert_chunks(chunks, llm.embed([c["text"] for c in chunks]))

        result = answer_question("QuickSort la gi?", "d1", chunks, llm, vector_store, settings)

        assert "answer" in result
        assert result["confidence"] in ("high", "low")
        assert len(result["retrieved_chunks"]) >= 1
    finally:
        vector_store.close()
        shutil.rmtree(tmp, ignore_errors=True)


def test_answer_question_reembeds_when_vector_store_lost_chunks():
    """Render free tier: Qdrant embedded chạy trên ổ đĩa tạm, mất khi restart --
    dù chunks đã bền vững trong DB (Turso), Qdrant có thể trống. answer_question
    phải tự phát hiện (count_for_doc == 0) và embed lại từ chunks trước khi search,
    thay vì trả lời "không tìm thấy" một cách sai lệch."""
    tmp = tempfile.mkdtemp()
    try:
        settings = Settings(qdrant_path=tmp, qdrant_vector_size=8)
        vector_store = VectorStore(path=tmp, url=None, collection="test_qa_reembed", vector_size=8)
        llm = MockLLMClient(embedding_dim=8)

        chunks = [{"chunk_id": "c1", "doc_id": "d1", "document_name": "doc.pdf", "page_number": 1,
                   "text": "QuickSort chon mot phan tu lam chot."}]
        # KHÔNG upsert vào vector_store trước -- mô phỏng đúng tình huống mất embedding.
        assert vector_store.count_for_doc("d1") == 0

        result = answer_question("QuickSort la gi?", "d1", chunks, llm, vector_store, settings)

        assert vector_store.count_for_doc("d1") == 1  # đã tự embed lại
        assert len(result["retrieved_chunks"]) >= 1
    finally:
        vector_store.close()
        shutil.rmtree(tmp, ignore_errors=True)


def test_answer_question_no_chunks_returns_low_confidence():
    tmp = tempfile.mkdtemp()
    try:
        settings = Settings(qdrant_path=tmp, qdrant_vector_size=8)
        vector_store = VectorStore(path=tmp, url=None, collection="test_qa_empty", vector_size=8)
        llm = MockLLMClient(embedding_dim=8)

        result = answer_question("Câu hỏi bất kỳ?", "d1", [], llm, vector_store, settings)

        assert result["confidence"] == "low"
        assert result["citations"] == []
    finally:
        vector_store.close()
        shutil.rmtree(tmp, ignore_errors=True)
