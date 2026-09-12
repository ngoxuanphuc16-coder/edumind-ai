import shutil
import tempfile

from app.services.hybrid_retrieval import hybrid_search
from app.services.llm_client import MockLLMClient
from app.services.vector_store import VectorStore


def test_hybrid_search_returns_relevant_chunks():
    tmp = tempfile.mkdtemp()
    try:
        vector_store = VectorStore(path=tmp, url=None, collection="test_hybrid", vector_size=8)
        llm = MockLLMClient(embedding_dim=8)

        chunks = [
            {"chunk_id": "c1", "doc_id": "d1", "document_name": "doc.pdf", "page_number": 1,
             "text": "QuickSort la thuat toan sap xep chia de tri."},
            {"chunk_id": "c2", "doc_id": "d1", "document_name": "doc.pdf", "page_number": 2,
             "text": "MergeSort cung la thuat toan chia de tri nhung on dinh hon."},
            {"chunk_id": "c3", "doc_id": "d1", "document_name": "doc.pdf", "page_number": 3,
             "text": "Cay nhi phan tim kiem ho tro tim kiem trong thoi gian logarit."},
        ]
        embeddings = llm.embed([c["text"] for c in chunks])
        vector_store.upsert_chunks(chunks, embeddings)

        results = hybrid_search("QuickSort hoat dong the nao?", "d1", chunks, llm, vector_store, top_k=2)

        assert 1 <= len(results) <= 2
        assert all(r["doc_id"] == "d1" for r in results)
    finally:
        vector_store.close()
        shutil.rmtree(tmp, ignore_errors=True)


def test_hybrid_search_filters_by_doc_id():
    tmp = tempfile.mkdtemp()
    try:
        vector_store = VectorStore(path=tmp, url=None, collection="test_hybrid_filter", vector_size=8)
        llm = MockLLMClient(embedding_dim=8)

        chunks_d1 = [{"chunk_id": "a1", "doc_id": "d1", "document_name": "a.pdf", "page_number": 1, "text": "noi dung A"}]
        chunks_d2 = [{"chunk_id": "b1", "doc_id": "d2", "document_name": "b.pdf", "page_number": 1, "text": "noi dung B"}]
        all_chunks = chunks_d1 + chunks_d2

        embeddings = llm.embed([c["text"] for c in all_chunks])
        vector_store.upsert_chunks(all_chunks, embeddings)

        results = hybrid_search("noi dung", "d1", chunks_d1, llm, vector_store, top_k=5)
        assert all(r["doc_id"] == "d1" for r in results)
    finally:
        vector_store.close()
        shutil.rmtree(tmp, ignore_errors=True)
