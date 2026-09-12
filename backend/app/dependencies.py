"""Singleton instances của các service, tạo 1 lần khi app khởi động
(tránh mở lại Qdrant local path hoặc tạo lại httpx.Client mỗi request)."""

from functools import lru_cache

from app.config import settings
from app.services.document_store import document_store
from app.services.llm_client import LLMClient, build_llm_client
from app.services.vector_store import VectorStore


@lru_cache
def get_llm_client() -> LLMClient:
    return build_llm_client(settings)


@lru_cache
def get_vector_store() -> VectorStore:
    return VectorStore(
        path=settings.qdrant_path,
        url=settings.qdrant_url,
        collection=settings.qdrant_collection,
        vector_size=settings.qdrant_vector_size,
    )


def get_document_store():
    return document_store
