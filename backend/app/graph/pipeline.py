from langgraph.graph import END, START, StateGraph

from app.config import Settings
from app.graph.nodes import make_node_functions
from app.graph.state import StudyState
from app.services.llm_client import LLMClient


def build_graph(llm: LLMClient, settings: Settings):
    """Lắp graph đúng theo implementation_plan.md mục 5:
    generate_roadmap <-> fact_checker (loop) -> build_dag -> generate_quiz -> finalize.
    """
    nodes = make_node_functions(llm, settings)

    workflow = StateGraph(StudyState)
    workflow.add_node("extract_kg", nodes["extract_kg"])
    workflow.add_node("generate_roadmap", nodes["generate_roadmap"])
    workflow.add_node("fact_checker", nodes["fact_checker"])
    workflow.add_node("build_dag", nodes["build_dag"])
    workflow.add_node("generate_quiz", nodes["generate_quiz"])
    workflow.add_node("finalize", nodes["finalize"])

    workflow.add_edge(START, "extract_kg")
    workflow.add_edge("extract_kg", "generate_roadmap")
    workflow.add_edge("generate_roadmap", "fact_checker")
    workflow.add_conditional_edges(
        "fact_checker",
        nodes["should_continue_loop"],
        {
            "approved": "build_dag",
            "approved_with_warning": "build_dag",
            "refine": "generate_roadmap",
        },
    )
    workflow.add_edge("build_dag", "generate_quiz")
    workflow.add_edge("generate_quiz", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()
