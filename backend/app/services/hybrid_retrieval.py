"""Hybrid retrieval (Dense + BM25) cho tính năng Q&A -- implementation_plan.md mục 2.

Đây là luồng dữ liệu THỨ HAI, tách biệt khỏi ingestion pipeline (mục 1): thay vì
duyệt toàn bộ chunk để sinh roadmap, ở đây truy vấn theo câu hỏi cụ thể của
sinh viên. Dense search dùng lại chunk đã embed vào Qdrant ở bước /upload;
BM25 dựng lại tại chỗ từ text các chunk của đúng tài liệu đó (rẻ, vì mỗi tài
liệu chỉ vài chục chunk).

Fusion dùng Reciprocal Rank Fusion (RRF) -- không cần chuẩn hoá thang điểm
giữa cosine similarity (Qdrant) và BM25 score, vốn không cùng đơn vị.

TODO chưa làm (nêu rõ, không giả vờ đã xong):
- Tokenize BM25 hiện chỉ lowercase + tách theo whitespace/dấu câu, CHƯA có
  word segmentation tiếng Việt thật (vd. underthesea/pyvi) -- ảnh hưởng chất
  lượng match cho từ ghép nhiều âm tiết.
"""

import re
from typing import List

from rank_bm25 import BM25Okapi

from app.graph.state import Chunk
from app.services.llm_client import LLMClient
from app.services.vector_store import VectorStore

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def hybrid_search(
    question: str,
    doc_id: str,
    chunks: List[Chunk],
    llm: LLMClient,
    vector_store: VectorStore,
    top_k: int = 5,
    rrf_k: int = 60,
) -> List[Chunk]:
    if not chunks:
        return []

    chunk_by_id = {c["chunk_id"]: c for c in chunks}

    # --- Dense (cosine similarity qua Qdrant, đã lọc theo doc_id) ---
    query_vector = llm.embed([question])[0]
    dense_hits = vector_store.search(query_vector, top_k=max(top_k * 2, 10), doc_id=doc_id)
    dense_rank = {hit.payload["chunk_id"]: rank for rank, hit in enumerate(dense_hits)}

    # --- BM25 (dựng tại chỗ, chỉ trong phạm vi chunk của tài liệu này) ---
    tokenized_corpus = [_tokenize(c["text"]) for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(_tokenize(question))
    bm25_ranked = sorted(range(len(chunks)), key=lambda i: bm25_scores[i], reverse=True)
    bm25_rank = {chunks[i]["chunk_id"]: rank for rank, i in enumerate(bm25_ranked)}

    # --- Reciprocal Rank Fusion ---
    all_ids = set(dense_rank) | set(bm25_rank)
    fused_scores = {
        cid: 1.0 / (rrf_k + dense_rank.get(cid, 10_000)) + 1.0 / (rrf_k + bm25_rank.get(cid, 10_000))
        for cid in all_ids
    }
    ranked_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)[:top_k]

    return [chunk_by_id[cid] for cid in ranked_ids if cid in chunk_by_id]
