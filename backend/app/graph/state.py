from operator import add
from typing import Annotated, List, Literal, Optional, TypedDict


class Chunk(TypedDict):
    chunk_id: str
    doc_id: str
    document_name: str
    page_number: int
    text: str


class KGTriplet(TypedDict):
    subject: str
    relation: str
    object: str
    source_chunk_id: str
    confidence: float


class StudyState(TypedDict):
    documents: List[dict]
    chunks: List[Chunk]
    kg_triplets: List[KGTriplet]
    draft_roadmap: List[dict]
    feedback_history: Annotated[List[str], add]   # tích lũy qua các vòng lặp, không ghi đè (mục 3.2)
    retry_count: int
    is_faithful: bool
    verification_status: Literal["pending", "approved", "approved_with_warning"]
    dag_order: List[str]
    graph_edges: List[dict]   # [{"source": node_id, "target": node_id}], cùng slug với draft_roadmap node_id
    broken_cycles: List[tuple]
    quiz: List[dict]
    final_roadmap: dict
    error: Optional[str]


def make_initial_state(documents: List[dict], chunks: List[Chunk], kg_triplets: List[KGTriplet]) -> StudyState:
    """Mỗi lần xử lý một tài liệu mới phải dùng state hoàn toàn mới -- không tái dùng
    retry_count/feedback_history của lần chạy trước (implementation_plan.md mục 5)."""
    return {
        "documents": documents,
        "chunks": chunks,
        "kg_triplets": kg_triplets,
        "draft_roadmap": [],
        "feedback_history": [],
        "retry_count": 0,
        "is_faithful": False,
        "verification_status": "pending",
        "dag_order": [],
        "graph_edges": [],
        "broken_cycles": [],
        "quiz": [],
        "final_roadmap": {},
        "error": None,
    }
