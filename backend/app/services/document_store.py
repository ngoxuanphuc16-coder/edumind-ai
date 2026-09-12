"""Lưu trữ document/roadmap bền vững qua libsql (SQLite-compatible; tương thích
Turso). Cùng 1 client code chạy được với file local (dev/test, không cần tài
khoản) lẫn database Turso từ xa (production, qua sync_url/auth_token) -- chỉ
khác cách khởi tạo connection.

Thay cho InMemoryDocumentStore trước đây: dữ liệu giờ sống ngoài RAM tiến
trình, không mất khi restart -- kể cả file PDF gốc (`pdf_bytes`), không chỉ
metadata/roadmap.

Giới hạn đã biết: chưa test được với Turso remote thật (chưa có tài khoản khi
viết code này) -- cơ chế embedded-replica (sync_url) dựa theo tài liệu chính
thức của libsql, cần verify lại khi có credentials thật (xem README)."""

import json
import threading
from typing import Optional

import libsql

from app.schemas import DocumentRecord

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    document_name TEXT NOT NULL,
    chunks TEXT NOT NULL,
    final_roadmap TEXT,
    pdf_bytes BLOB NOT NULL
)
"""


class SqlDocumentStore:
    def __init__(self, db_path: str, sync_url: Optional[str] = None, auth_token: Optional[str] = None):
        self._lock = threading.Lock()
        if sync_url:
            self._conn = libsql.connect(db_path, sync_url=sync_url, auth_token=auth_token or "")
            self._conn.sync()  # kéo dữ liệu mới nhất từ Turso về trước khi phục vụ request
        else:
            self._conn = libsql.connect(db_path, _check_same_thread=False)
        self._conn.execute(_CREATE_TABLE_SQL)
        self._conn.commit()
        self._sync_on_write = bool(sync_url)

    def save(self, record: DocumentRecord) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO documents (doc_id, document_name, chunks, final_roadmap, pdf_bytes)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    document_name = excluded.document_name,
                    chunks = excluded.chunks,
                    final_roadmap = excluded.final_roadmap,
                    pdf_bytes = excluded.pdf_bytes
                """,
                (
                    record.doc_id,
                    record.document_name,
                    json.dumps(record.chunks),
                    json.dumps(record.final_roadmap) if record.final_roadmap is not None else None,
                    record.pdf_bytes,
                ),
            )
            self._conn.commit()
            if self._sync_on_write:
                self._conn.sync()

    def get(self, doc_id: str) -> Optional[DocumentRecord]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT doc_id, document_name, chunks, final_roadmap, pdf_bytes FROM documents WHERE doc_id = ?",
                (doc_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        doc_id, document_name, chunks_json, final_roadmap_json, pdf_bytes = row
        return DocumentRecord(
            doc_id=doc_id,
            document_name=document_name,
            chunks=json.loads(chunks_json),
            final_roadmap=json.loads(final_roadmap_json) if final_roadmap_json is not None else None,
            pdf_bytes=pdf_bytes,
        )

    def close(self) -> None:
        self._conn.close()
