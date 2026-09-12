"""LLM client abstraction.

Tách interface (Protocol) khỏi implementation để:
- MockLLMClient chạy được ngay không cần cài gì (dev/test, mặc định trong .env).
- OllamaLLMClient gọi Ollama thật một khi đã cài (đổi LLM_PROVIDER=ollama trong .env).
- fact-checker và generator dùng 2 model KHÁC NHAU (generator_model / checker_model)
  để tránh việc một model tự chấm điểm chính mình rồi luôn tự tin là đúng
  (implementation_plan.md mục 3.1).
"""

import json
from typing import List, Optional, Protocol

import httpx

from app.graph.state import Chunk
from app.utils import slugify


class LLMClient(Protocol):
    def generate_roadmap(
        self, chunks: List[Chunk], feedback_history: List[str], kg_triplets: Optional[List[dict]] = None
    ) -> List[dict]: ...

    def judge_faithfulness(self, draft_roadmap: List[dict], chunks: List[Chunk]) -> dict: ...

    def extract_kg_triplets(self, chunks: List[Chunk]) -> List[dict]: ...

    def generate_quiz(self, draft_roadmap: List[dict]) -> List[dict]: ...

    def embed(self, texts: List[str]) -> List[List[float]]: ...

    def answer_question(self, question: str, chunks: List[Chunk], feedback: str = "") -> dict: ...


# ---------------------------------------------------------------------------
# Mock client -- dùng để chạy/test pipeline mà không cần Ollama.
# Hành vi lấy đúng ý tưởng từ demo_graph.py: nếu đã có feedback_history thì
# "sửa" lại citation cho khớp chunk gốc, mô phỏng một generator biết tự sửa lỗi.
# ---------------------------------------------------------------------------

class MockLLMClient:
    def __init__(self, embedding_dim: int = 768):
        # Phải khớp settings.qdrant_vector_size, nếu không Qdrant sẽ reject lúc upsert
        # (ValueError: could not broadcast input array ...).
        self.embedding_dim = embedding_dim

    def generate_roadmap(
        self, chunks: List[Chunk], feedback_history: List[str], kg_triplets: Optional[List[dict]] = None
    ) -> List[dict]:
        if not chunks:
            return []
        kg_triplets = kg_triplets or []
        chunk_by_id = {c["chunk_id"]: c for c in chunks}

        def make_node(node_id: str, title: str, chunk: Chunk, quote: str) -> dict:
            return {
                "node_id": node_id,
                "title": title,
                "importance": "CRITICAL",
                "summary": quote[:80],
                "citations": [{
                    "document_name": chunk["document_name"],
                    "page_number": chunk["page_number"],
                    "exact_quote": quote,
                    "source_chunk_id": chunk["chunk_id"],
                }],
            }

        if not kg_triplets:
            # Tài liệu quá ngắn để trích KG (vd. 1 chunk) -- fallback: 1 node duy nhất,
            # không có graph_edges (build_dag_node sẽ trả graph_edges rỗng tương ứng).
            chunk = chunks[0]
            quote = chunk["text"][:200] if feedback_history else "Khái niệm này không có trong tài liệu gốc (mock lần đầu)"
            return [make_node("node_01", f"Khái niệm từ {chunk['document_name']} (trang {chunk['page_number']})", chunk, quote)]

        # Có KG -- 1 node cho mỗi khái niệm duy nhất, node_id = slug(tên khái niệm) để
        # khớp CHÍNH XÁC với graph_edges (build_dag_node dùng cùng hàm slugify trên cùng
        # tên khái niệm), nhờ đó frontend vẽ được sơ đồ node-cạnh nối liền mạch.
        #
        # QUAN TRỌNG: map concept -> chunk phải tra thẳng từ `chunks` (concept = chunk
        # text[:30] theo đúng cách extract_kg_triplets mock dựng), KHÔNG được suy ra từ
        # triplet["source_chunk_id"] -- vì source_chunk_id của 1 triplet chỉ đúng cho vai
        # trò "subject" (chunk[i]); nếu gán luôn cho "object" (chunk[i+1]) thì object sẽ bị
        # trỏ NHẦM sang chunk của subject, khiến citation/trang hiển thị sai (bug đã gặp
        # khi test: node "QuickSort" trích dẫn nhầm sang trang của node đứng trước nó).
        text_to_chunk = {c["text"][:30]: c["chunk_id"] for c in chunks}
        concept_source_chunk: dict[str, str] = {}
        for t in kg_triplets:
            for concept in (t["subject"], t["object"]):
                concept_source_chunk.setdefault(concept, text_to_chunk.get(concept, chunks[0]["chunk_id"]))

        nodes = []
        for i, (concept, source_chunk_id) in enumerate(concept_source_chunk.items()):
            chunk = chunk_by_id.get(source_chunk_id, chunks[0])
            # Mô phỏng lỗi ở node đầu tiên trong lần thử đầu, để vòng lặp fact-check vẫn
            # có gì đó để "sửa" khi demo (giống hành vi cũ trước khi có nhiều node).
            is_first_attempt_error = not feedback_history and i == 0
            quote = "Khái niệm bịa, không có trong tài liệu gốc" if is_first_attempt_error else chunk["text"][:200]
            nodes.append(make_node(slugify(concept), concept, chunk, quote))
        return nodes

    def judge_faithfulness(self, draft_roadmap: List[dict], chunks: List[Chunk]) -> dict:
        return {"faithfulness_score": 0.97, "feedback": "[mock] giả định đạt ngưỡng trung thực."}

    def extract_kg_triplets(self, chunks: List[Chunk]) -> List[dict]:
        if len(chunks) < 2:
            return []
        return [{
            "subject": chunks[i]["text"][:30],
            "relation": "CẦN_TRƯỚC",
            "object": chunks[i + 1]["text"][:30],
            "source_chunk_id": chunks[i]["chunk_id"],
            "confidence": 0.9,
        } for i in range(len(chunks) - 1)]

    def generate_quiz(self, draft_roadmap: List[dict]) -> List[dict]:
        return [{"question": f"Giải thích: {n['title']}", "type": "short_answer"} for n in draft_roadmap]

    def embed(self, texts: List[str]) -> List[List[float]]:
        # vector giả (deterministic theo độ dài chuỗi) -- CHỈ để pipeline chạy được khi test,
        # không dùng để đánh giá chất lượng semantic search thật.
        return [[float(len(t) % 97)] * self.embedding_dim for t in texts]

    def answer_question(self, question: str, chunks: List[Chunk], feedback: str = "") -> dict:
        if not chunks:
            return {"answer": "Không tìm thấy đoạn tài liệu nào liên quan.", "citations": []}
        chunk = chunks[0]
        quote = chunk["text"][:200] if feedback else "Câu trả lời bịa, không có trong tài liệu (mock lần đầu)"
        return {
            "answer": f"[mock] Trả lời cho '{question}' dựa trên {chunk['document_name']} trang {chunk['page_number']}.",
            "citations": [{
                "document_name": chunk["document_name"],
                "page_number": chunk["page_number"],
                "exact_quote": quote,
                "source_chunk_id": chunk["chunk_id"],
            }],
        }


# ---------------------------------------------------------------------------
# Ollama client thật -- cần: `ollama serve` đang chạy + đã pull đủ 3 model
# (xem README.md). Prompt ở đây là điểm khởi đầu, gần như chắc chắn cần
# tinh chỉnh thêm sau khi thấy output thật từ model bạn chọn.
# ---------------------------------------------------------------------------

class OllamaResponseError(Exception):
    pass


class OllamaLLMClient:
    def __init__(self, base_url: str, generator_model: str, checker_model: str, embedding_model: str):
        self.generator_model = generator_model
        self.checker_model = checker_model
        self.embedding_model = embedding_model
        self._client = httpx.Client(base_url=base_url, timeout=180.0)

    def _generate(self, model: str, prompt: str) -> str:
        resp = self._client.post("/api/generate", json={"model": model, "prompt": prompt, "stream": False})
        resp.raise_for_status()
        return resp.json()["response"]

    def _generate_json(self, model: str, prompt: str, max_retries: int = 2) -> dict:
        """Ép output JSON + validate + retry -- addressing việc LLM output sai định dạng
        (implementation_plan.md mục 7: 'Validate output LLM')."""
        last_error = None
        for attempt in range(max_retries + 1):
            raw = self._generate(model, prompt)
            try:
                start, end = raw.index("{"), raw.rindex("}") + 1
                return json.loads(raw[start:end])
            except (ValueError, json.JSONDecodeError) as e:
                last_error = e
                prompt = prompt + f"\n\nOutput trước đó KHÔNG phải JSON hợp lệ ({e}). Chỉ trả về JSON, không thêm chữ nào khác."
        raise OllamaResponseError(f"Model {model} không trả JSON hợp lệ sau {max_retries} lần retry: {last_error}")

    def generate_roadmap(
        self, chunks: List[Chunk], feedback_history: List[str], kg_triplets: Optional[List[dict]] = None
    ) -> List[dict]:
        context = "\n\n".join(f"[Trang {c['page_number']}] {c['text']}" for c in chunks)
        feedback_block = ""
        if feedback_history:
            feedback_block = "\n\nCác lỗi ĐÃ PHÁT HIỆN ở những lần trước, PHẢI sửa:\n" + "\n".join(
                f"- {f}" for f in feedback_history
            )
        concepts = sorted({t["subject"] for t in (kg_triplets or [])} | {t["object"] for t in (kg_triplets or [])})
        concept_block = ""
        if concepts:
            concept_block = (
                "\n\nDanh sách khái niệm ĐÃ được trích xuất từ knowledge graph của tài liệu này -- "
                "BẮT BUỘC dùng CHÍNH XÁC các tên này làm 'title' cho node tương ứng (không đổi cách viết), "
                "để sơ đồ roadmap khớp với graph phụ thuộc đã dựng:\n" + "\n".join(f"- {c}" for c in concepts)
            )
        prompt = f"""Bạn là trợ lý học tập. Dựa CHỈ VÀO nội dung tài liệu dưới đây, hãy trích ra các khái niệm
quan trọng nhất thành một roadmap học tập. TUYỆT ĐỐI không thêm khái niệm không có trong tài liệu.

Tài liệu:
{context}
{concept_block}
{feedback_block}

Trả về JSON theo đúng format:
{{"nodes": [{{"node_id": "...", "title": "...", "importance": "CRITICAL|IMPORTANT|OPTIONAL",
"summary": "...", "citations": [{{"document_name": "...", "page_number": 0,
"exact_quote": "câu trích nguyên văn từ tài liệu", "source_chunk_id": "..."}}]}}]}}"""
        data = self._generate_json(self.generator_model, prompt)
        return data.get("nodes", [])

    def judge_faithfulness(self, draft_roadmap: List[dict], chunks: List[Chunk]) -> dict:
        chunk_by_id = {c["chunk_id"]: c for c in chunks}
        items = []
        for node in draft_roadmap:
            for citation in node["citations"]:
                src = chunk_by_id.get(citation["source_chunk_id"], {}).get("text", "")
                items.append(f"Khái niệm: {node['title']}\nTrích dẫn: {citation['exact_quote']}\nNguồn gốc: {src}")
        prompt = f"""Bạn là người kiểm chứng nghiêm khắc. Với mỗi cặp (khái niệm, trích dẫn, nguồn gốc) dưới đây,
đánh giá xem trích dẫn có THỰC SỰ xuất hiện trong nguồn gốc không, và khái niệm có được nguồn gốc hỗ trợ không.

{chr(10).join(items)}

Trả về JSON: {{"faithfulness_score": 0.0-1.0, "feedback": "mô tả cụ thể phần nào không được nguồn gốc hỗ trợ"}}"""
        return self._generate_json(self.checker_model, prompt)

    def extract_kg_triplets(self, chunks: List[Chunk]) -> List[dict]:
        context = "\n\n".join(f"[chunk_id={c['chunk_id']}] {c['text']}" for c in chunks)
        prompt = f"""Trích xuất quan hệ "cần học trước" giữa các khái niệm trong tài liệu sau, dạng triplet.

{context}

Trả về JSON: {{"triplets": [{{"subject": "...", "relation": "CẦN_TRƯỚC", "object": "...",
"source_chunk_id": "...", "confidence": 0.0-1.0}}]}}"""
        data = self._generate_json(self.generator_model, prompt)
        return data.get("triplets", [])

    def generate_quiz(self, draft_roadmap: List[dict]) -> List[dict]:
        titles = "\n".join(f"- {n['title']}" for n in draft_roadmap)
        prompt = f"""Tạo 1 câu hỏi ngắn cho mỗi khái niệm sau, chỉ dựa trên tên khái niệm:
{titles}

Trả về JSON: {{"quiz": [{{"question": "...", "type": "short_answer"}}]}}"""
        data = self._generate_json(self.generator_model, prompt)
        return data.get("quiz", [])

    def embed(self, texts: List[str]) -> List[List[float]]:
        out = []
        for t in texts:
            resp = self._client.post("/api/embeddings", json={"model": self.embedding_model, "prompt": t})
            resp.raise_for_status()
            out.append(resp.json()["embedding"])
        return out

    def answer_question(self, question: str, chunks: List[Chunk], feedback: str = "") -> dict:
        context = "\n\n".join(f"[chunk_id={c['chunk_id']}, trang {c['page_number']}] {c['text']}" for c in chunks)
        feedback_block = f"\n\nLần trả lời trước bị lỗi: {feedback}\nHãy sửa lại, CHỈ dùng thông tin có trong đoạn trích trên." if feedback else ""
        prompt = f"""Trả lời câu hỏi của sinh viên CHỈ dựa vào các đoạn trích dưới đây. Nếu không đủ thông tin,
nói rõ là tài liệu không đề cập, TUYỆT ĐỐI không bịa.

Các đoạn trích:
{context}

Câu hỏi: {question}
{feedback_block}

Trả về JSON: {{"answer": "...", "citations": [{{"document_name": "...", "page_number": 0,
"exact_quote": "câu trích nguyên văn từ đoạn trích", "source_chunk_id": "..."}}]}}"""
        return self._generate_json(self.generator_model, prompt)


def build_llm_client(settings) -> LLMClient:
    if settings.llm_provider == "mock":
        return MockLLMClient(embedding_dim=settings.qdrant_vector_size)
    return OllamaLLMClient(
        base_url=settings.ollama_base_url,
        generator_model=settings.ollama_generator_model,
        checker_model=settings.ollama_checker_model,
        embedding_model=settings.ollama_embedding_model,
    )
