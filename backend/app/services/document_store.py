"""Lưu trữ document/roadmap tạm thời trong bộ nhớ tiến trình.

CHƯA phải DB thật -- mất dữ liệu khi restart server. Đủ dùng để dựng khung
và test luồng end-to-end; thay bằng SQLite/Postgres khi cần persistent thật
(không nằm trong phạm vi bản scaffold này)."""

from threading import Lock
from typing import Optional

from app.schemas import DocumentRecord


class InMemoryDocumentStore:
    def __init__(self):
        self._data: dict[str, DocumentRecord] = {}
        self._lock = Lock()

    def save(self, record: DocumentRecord) -> None:
        with self._lock:
            self._data[record.doc_id] = record

    def get(self, doc_id: str) -> Optional[DocumentRecord]:
        return self._data.get(doc_id)


document_store = InMemoryDocumentStore()
