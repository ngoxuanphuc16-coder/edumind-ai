"""Wrapper quanh qdrant-client.

Mặc định dùng chế độ local/embedded (`QdrantClient(path=...)`) -- KHÔNG cần
cài Docker hay chạy Qdrant server riêng, phù hợp máy dev hiện tại (đã kiểm tra:
chưa có Docker). Khi cần scale/triển khai thật, đặt QDRANT_URL trong .env để
chuyển sang Qdrant server (xem docker-compose.yml).
"""

from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.graph.state import Chunk


class VectorStore:
    def __init__(self, path: Optional[str], url: Optional[str], collection: str, vector_size: int):
        if url:
            self.client = QdrantClient(url=url)
        else:
            self.client = QdrantClient(path=path)
        self.collection = collection
        self.vector_size = vector_size
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection not in existing:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qmodels.VectorParams(size=self.vector_size, distance=qmodels.Distance.COSINE),
            )

    def upsert_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        points = [
            qmodels.PointStruct(id=self._point_id(chunk["chunk_id"]), vector=emb, payload=dict(chunk))
            for chunk, emb in zip(chunks, embeddings)
        ]
        self.client.upsert(collection_name=self.collection, points=points)

    def search(self, query_vector: List[float], top_k: int = 5, doc_id: Optional[str] = None):
        query_filter = None
        if doc_id:
            query_filter = qmodels.Filter(
                must=[qmodels.FieldCondition(key="doc_id", match=qmodels.MatchValue(value=doc_id))]
            )
        # search() bị loại khỏi qdrant-client >=1.15 -- query_points() là API thay thế.
        response = self.client.query_points(
            collection_name=self.collection, query=query_vector, limit=top_k, query_filter=query_filter
        )
        return response.points

    @staticmethod
    def _point_id(chunk_id: str) -> int:
        # Qdrant point id cần là int hoặc UUID; băm chunk_id thành int ổn định.
        return abs(hash(chunk_id)) % (2**63)

    def close(self) -> None:
        # Ở chế độ embedded (path=...), Qdrant giữ file lock trên sqlite -- cần đóng
        # tường minh trước khi xoá thư mục (quan trọng trên Windows, xoá file đang
        # mở sẽ ném PermissionError).
        self.client.close()
