import shutil
import tempfile

import pytest

from app.schemas import DocumentRecord
from app.services.document_store import SqlDocumentStore


@pytest.fixture
def store():
    tmp_dir = tempfile.mkdtemp()
    db_path = f"{tmp_dir}/test.db"
    s = SqlDocumentStore(db_path=db_path, sync_url=None, auth_token=None)
    yield s
    s.close()
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_save_and_get_roundtrip(store):
    record = DocumentRecord(
        doc_id="doc-1",
        document_name="test.pdf",
        chunks=[{"chunk_id": "doc-1_p1", "text": "hello"}],
        final_roadmap=None,
        pdf_bytes=b"%PDF-1.4 fake bytes",
    )

    store.save(record)
    fetched = store.get("doc-1")

    assert fetched is not None
    assert fetched.doc_id == "doc-1"
    assert fetched.document_name == "test.pdf"
    assert fetched.chunks == [{"chunk_id": "doc-1_p1", "text": "hello"}]
    assert fetched.final_roadmap is None
    assert fetched.pdf_bytes == b"%PDF-1.4 fake bytes"


def test_get_unknown_doc_id_returns_none(store):
    assert store.get("does-not-exist") is None


def test_save_twice_updates_record(store):
    record = DocumentRecord(
        doc_id="doc-2", document_name="a.pdf", chunks=[], final_roadmap=None, pdf_bytes=b"abc",
    )
    store.save(record)

    record.final_roadmap = {"verification_status": "approved"}
    store.save(record)

    fetched = store.get("doc-2")
    assert fetched.final_roadmap == {"verification_status": "approved"}
