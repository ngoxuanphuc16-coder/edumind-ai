"""Lớp kiểm chứng cứng (Lớp 1) -- không dùng LLM (implementation_plan.md mục 3.1 / mục 6).

Fuzzy-match `exact_quote` với đúng chunk gốc theo `source_chunk_id`, sau khi
chuẩn hoá whitespace -- không dùng substring tuyệt đối vì tài liệu OCR gần như
luôn lệch khoảng trắng/dấu câu.
"""

import difflib
from typing import List

from app.graph.state import Chunk


def _normalize(s: str) -> str:
    return " ".join(s.split())


def citation_match_ratio(quote: str, chunk_text: str) -> float:
    q, c = _normalize(quote), _normalize(chunk_text)
    if not q:
        return 0.0
    match = difflib.SequenceMatcher(None, q, c).find_longest_match(0, len(q), 0, len(c))
    return (match.size / len(q)) * 100


def verify_citations_against_chunks(draft_roadmap: List[dict], chunks: List[Chunk], threshold: float) -> dict:
    chunk_by_id = {c["chunk_id"]: c for c in chunks}
    total, matched, unmatched = 0, 0, []

    for node in draft_roadmap:
        for citation in node.get("citations", []):
            total += 1
            chunk = chunk_by_id.get(citation.get("source_chunk_id"))
            ratio = citation_match_ratio(citation.get("exact_quote", ""), chunk["text"]) if chunk else 0.0
            if ratio >= threshold:
                matched += 1
            else:
                unmatched.append({
                    "node_id": node.get("node_id"),
                    "quote_preview": citation.get("exact_quote", "")[:60],
                    "match_ratio": round(ratio, 1),
                })

    coverage_ratio = (matched / total) if total else 0.0
    return {"coverage_ratio": coverage_ratio, "unmatched_citations": unmatched}
