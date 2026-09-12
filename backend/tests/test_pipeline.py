"""Verify đúng 3 nhánh của vòng lặp anti-hallucination (giống demo_graph.py),
nhưng chạy qua code thật trong app/graph/, không phải script demo riêng."""

from app.config import Settings
from app.graph.pipeline import build_graph
from app.graph.state import make_initial_state
from app.services.llm_client import LLMClient, MockLLMClient


class ScenarioLLM:
    """LLM giả lập có kịch bản cố định, dùng lại đúng ý tưởng demo_graph.py:
    behavior kiểm soát generator có tự sửa lỗi sau feedback hay không."""

    def __init__(self, behavior: str):
        self.behavior = behavior

    def generate_roadmap(self, chunks, feedback_history, kg_triplets=None):
        chunk = chunks[0]
        if self.behavior == "always_correct":
            quote = chunk["text"]
        elif self.behavior == "fixes_after_feedback":
            quote = chunk["text"] if feedback_history else "Khái niệm bịa, không có trong tài liệu"
        else:  # never_fixes
            quote = "Khái niệm bịa, không có trong tài liệu"
        return [{
            "node_id": "node_01", "title": "test",
            "citations": [{"document_name": chunk["document_name"], "page_number": chunk["page_number"],
                           "exact_quote": quote, "source_chunk_id": chunk["chunk_id"]}],
        }]

    def judge_faithfulness(self, draft_roadmap, chunks):
        return {"faithfulness_score": 0.97, "feedback": "ok"}

    def extract_kg_triplets(self, chunks):
        return []

    def generate_quiz(self, draft_roadmap):
        return [{"question": "q", "type": "short_answer"} for _ in draft_roadmap]

    def embed(self, texts):
        return [[0.0] * 8 for _ in texts]


def _run(behavior: str):
    settings = Settings(llm_provider="mock", max_retries=3, faithfulness_threshold=0.85)
    llm: LLMClient = ScenarioLLM(behavior)
    graph = build_graph(llm, settings)
    chunk = {"chunk_id": "c1", "doc_id": "d1", "document_name": "doc.pdf", "page_number": 1, "text": "Nội dung gốc."}
    state = make_initial_state(documents=[{"doc_id": "d1"}], chunks=[chunk], kg_triplets=[])
    return graph.invoke(state)


def test_approved_on_first_try():
    result = _run("always_correct")
    assert result["final_roadmap"]["verification_status"] == "approved"
    assert result["final_roadmap"]["retry_count"] == 1


def test_approved_after_refine():
    result = _run("fixes_after_feedback")
    assert result["final_roadmap"]["verification_status"] == "approved"
    assert result["final_roadmap"]["retry_count"] == 2
    # 2 lượt fact-check chạy tổng cộng (1 fail + 1 approved) -> mỗi lượt đều để lại
    # 1 dòng feedback (kể cả lượt đạt, làm audit trail), nên tích lũy đúng 2 dòng.
    assert len(result["feedback_history"]) == 2


def test_approved_with_warning_after_max_retries():
    result = _run("never_fixes")
    assert result["final_roadmap"]["verification_status"] == "approved_with_warning"
    assert result["final_roadmap"]["retry_count"] == 3
    assert len(result["feedback_history"]) == 3  # feedback tích lũy qua cả 3 lượt, không bị ghi đè


def test_final_roadmap_always_populated():
    for behavior in ("always_correct", "fixes_after_feedback", "never_fixes"):
        result = _run(behavior)
        assert result["final_roadmap"]  # không bao giờ rỗng, kể cả nhánh warning


def test_graph_edges_reference_valid_node_ids():
    """Tính năng roadmap dạng đồ thị (giống roadmap.sh) cần graph_edges.source/target
    khớp CHÍNH XÁC với node_id trong roadmap -- nếu không frontend không vẽ được cạnh nối."""
    settings = Settings(llm_provider="mock", max_retries=3, faithfulness_threshold=0.85)
    llm = MockLLMClient(embedding_dim=8)
    graph = build_graph(llm, settings)
    chunks = [
        {"chunk_id": "c1", "doc_id": "d1", "document_name": "doc.pdf", "page_number": 1, "text": "Mang va con tro."},
        {"chunk_id": "c2", "doc_id": "d1", "document_name": "doc.pdf", "page_number": 2, "text": "QuickSort."},
        {"chunk_id": "c3", "doc_id": "d1", "document_name": "doc.pdf", "page_number": 3, "text": "Do phuc tap."},
    ]
    state = make_initial_state(documents=[{"doc_id": "d1"}], chunks=chunks, kg_triplets=[])
    result = graph.invoke(state)

    final = result["final_roadmap"]
    assert len(final["roadmap"]) > 1  # nhiều chunk -> nhiều khái niệm, không còn fallback 1 node
    node_ids = {n["node_id"] for n in final["roadmap"]}
    assert final["graph_edges"]  # phải có ít nhất 1 cạnh nối
    for edge in final["graph_edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids
