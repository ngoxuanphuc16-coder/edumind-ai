from app.services.llm_client import MockLLMClient


def test_generate_roadmap_citations_point_to_correct_chunk():
    """Regression: mỗi node phải trích dẫn ĐÚNG chunk chứa khái niệm đó, không phải
    chunk của khái niệm tiên quyết đứng trước nó (bug: concept_source_chunk từng suy
    nhầm từ triplet['source_chunk_id'], khiến node 'QuickSort' trích dẫn nhầm sang
    trang của 'Mang va con tro')."""
    llm = MockLLMClient(embedding_dim=8)
    chunks = [
        {"chunk_id": "c1", "doc_id": "d1", "document_name": "doc.pdf", "page_number": 1, "text": "Mang va con tro."},
        {"chunk_id": "c2", "doc_id": "d1", "document_name": "doc.pdf", "page_number": 2, "text": "QuickSort la gi."},
        {"chunk_id": "c3", "doc_id": "d1", "document_name": "doc.pdf", "page_number": 3, "text": "Do phuc tap O(n)."},
    ]
    kg_triplets = llm.extract_kg_triplets(chunks)

    roadmap = llm.generate_roadmap(chunks, feedback_history=["dummy"], kg_triplets=kg_triplets)

    by_title = {n["title"]: n for n in roadmap}
    assert by_title["Mang va con tro."]["citations"][0]["page_number"] == 1
    assert by_title["QuickSort la gi."]["citations"][0]["page_number"] == 2
    assert by_title["Do phuc tap O(n)."]["citations"][0]["page_number"] == 3
