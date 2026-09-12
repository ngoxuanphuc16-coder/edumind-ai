from app.config import Settings
from app.graph.dag import detect_and_break_cycles, topological_sort
from app.graph.state import StudyState
from app.graph.verification import verify_citations_against_chunks
from app.services.llm_client import LLMClient


def make_node_functions(llm: LLMClient, settings: Settings):
    """Trả về dict các node function đã bind sẵn llm client + settings, để
    pipeline.py lắp vào StateGraph. Tách riêng khỏi pipeline.py cho dễ test
    từng node độc lập."""

    def extract_kg_node(state: StudyState) -> dict:
        # Parse (PDF -> chunks) đã xong ở API layer trước khi invoke graph (I/O thuần,
        # không cần retry/LLM). Node này chỉ làm phần cần LLM: trích KG triplet.
        triplets = llm.extract_kg_triplets(state["chunks"])
        return {"kg_triplets": triplets}

    def generate_roadmap_node(state: StudyState) -> dict:
        draft = llm.generate_roadmap(state["chunks"], state.get("feedback_history", []))
        return {"draft_roadmap": draft}

    def fact_checker_node(state: StudyState) -> dict:
        hard_check = verify_citations_against_chunks(
            state["draft_roadmap"], state["chunks"], settings.citation_match_threshold
        )

        # Fail-fast (mục 8): coverage quá thấp thì khỏi tốn lệnh gọi LLM judge.
        if hard_check["coverage_ratio"] < 0.5:
            llm_score = 0.0
            feedback = f"[fail-fast] citation lệch nặng với tài liệu gốc: {hard_check['unmatched_citations']}"
        else:
            judge = llm.judge_faithfulness(state["draft_roadmap"], state["chunks"])
            llm_score = judge["faithfulness_score"]
            feedback = judge["feedback"]

        combined_score = min(hard_check["coverage_ratio"], llm_score)
        is_faithful = combined_score >= settings.faithfulness_threshold and not hard_check["unmatched_citations"]
        retry_count = state.get("retry_count", 0) + 1

        if is_faithful:
            status = "approved"
        elif retry_count >= settings.max_retries:
            status = "approved_with_warning"
        else:
            status = "pending"

        return {
            "is_faithful": is_faithful,
            "verification_status": status,
            "feedback_history": [feedback],
            "retry_count": retry_count,
        }

    def build_dag_node(state: StudyState) -> dict:
        acyclic, broken = detect_and_break_cycles(state["kg_triplets"])
        return {"dag_order": topological_sort(acyclic), "broken_cycles": broken}

    def generate_quiz_node(state: StudyState) -> dict:
        return {"quiz": llm.generate_quiz(state["draft_roadmap"])}

    def finalize_node(state: StudyState) -> dict:
        return {"final_roadmap": {
            "roadmap": state["draft_roadmap"],
            "dag_order": state["dag_order"],
            "quiz": state["quiz"],
            "verification_status": state["verification_status"],
            "retry_count": state["retry_count"],
        }}

    def should_continue_loop(state: StudyState) -> str:
        return "refine" if state["verification_status"] == "pending" else state["verification_status"]

    return {
        "extract_kg": extract_kg_node,
        "generate_roadmap": generate_roadmap_node,
        "fact_checker": fact_checker_node,
        "build_dag": build_dag_node,
        "generate_quiz": generate_quiz_node,
        "finalize": finalize_node,
        "should_continue_loop": should_continue_loop,
    }
