import base64
import io
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_vector_store
from app.main import app
from app.services.vector_store import VectorStore

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_vector_store():
    # Không dùng singleton mặc định (./data/qdrant_local) -- nếu backend dev server
    # đang chạy song song, nó giữ file lock trên đúng thư mục đó (Qdrant embedded
    # mode chỉ cho 1 process truy cập tại 1 thời điểm), khiến test fail dù code đúng.
    tmp = tempfile.mkdtemp()
    store = VectorStore(path=tmp, url=None, collection="test_qa_api", vector_size=768)
    app.dependency_overrides[get_vector_store] = lambda: store
    yield
    app.dependency_overrides.pop(get_vector_store, None)
    store.close()
    shutil.rmtree(tmp, ignore_errors=True)

# PDF nhỏ 1 trang chứa text "QuickSort chon mot phan tu lam chot va phan chia mang thanh hai mang con."
# (tạo sẵn bằng fpdf2, nhúng base64 để test không cần thêm dependency runtime).
_SAMPLE_PDF_B64 = (
    "JVBERi0xLjMKJenr8b8KMSAwIG9iago8PAovQ291bnQgMQovS2lkcyBbMyAwIFJdCi9NZWRpYUJveCBbMCAwIDU5NS4yOCA4NDEuODld"
    "Ci9UeXBlIC9QYWdlcwo+PgplbmRvYmoKMiAwIG9iago8PAovT3BlbkFjdGlvbiBbMyAwIFIgL0ZpdEggbnVsbF0KL1BhZ2VMYXlvdXQg"
    "L09uZUNvbHVtbgovUGFnZXMgMSAwIFIKL1R5cGUgL0NhdGFsb2cKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL0NvbnRlbnRzIDQgMCBSCi9Q"
    "YXJlbnQgMSAwIFIKL1Jlc291cmNlcyA2IDAgUgovVHlwZSAvUGFnZQo+PgplbmRvYmoKNCAwIG9iago8PAovRmlsdGVyIC9GbGF0ZURl"
    "Y29kZQovTGVuZ3RoIDExNwo+PgpzdHJlYW0KeJwlzTEOwjAMRuG9p/hHWExSVAVWJBi6IXwBKwgcIAlCbrk+RB3ft7weY+doCPh2B8bm"
    "5OF7cg58w5EbbT35HcJ+oBDAV6zOU4rPS/0YotaCXA1vlQKb8JLc0DDLYlGTIEu5w/6pUElLxlpoDX60yQ/qfiX5CmVuZHN0cmVhbQpl"
    "bmRvYmoKNSAwIG9iago8PAovQmFzZUZvbnQgL0hlbHZldGljYQovRW5jb2RpbmcgL1dpbkFuc2lFbmNvZGluZwovU3VidHlwZSAvVHlw"
    "ZTEKL1R5cGUgL0ZvbnQKPj4KZW5kb2JqCjYgMCBvYmoKPDwKL0ZvbnQgPDwvRjEgNSAwIFI+PgovUHJvY1NldCBbL1BERiAvVGV4dCAv"
    "SW1hZ2VCIC9JbWFnZUMgL0ltYWdlSV0KPj4KZW5kb2JqCjcgMCBvYmoKPDwKL0NyZWF0aW9uRGF0ZSAoRDoyMDI2MDkxMjA0MzgwNVop"
    "Cj4+CmVuZG9iagp4cmVmCjAgOAowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMTUgMDAwMDAgbiAKMDAwMDAwMDEwMiAwMDAwMCBu"
    "IAowMDAwMDAwMjA1IDAwMDAwIG4gCjAwMDAwMDAyODUgMDAwMDAgbiAKMDAwMDAwMDQ3NCAwMDAwMCBuIAowMDAwMDAwNTcxIDAwMDAw"
    "IG4gCjAwMDAwMDA2NTggMDAwMDAgbiAKdHJhaWxlcgo8PAovU2l6ZSA4Ci9Sb290IDIgMCBSCi9JbmZvIDcgMCBSCi9JRCBbPDkzQzdD"
    "OTlFMTkwRjk3MzEzMUQwN0Y4RjE2MDM3MEQwPjw5M0M3Qzk5RTE5MEY5NzMxMzFEMDdGOEYxNjAzNzBEMD5dCj4+CnN0YXJ0eHJlZgo3"
    "MTMKJSVFT0YK"
)


def _upload_sample_doc() -> str:
    pdf_bytes = base64.b64decode(_SAMPLE_PDF_B64)
    resp = client.post(
        "/documents/upload",
        files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["doc_id"]


def test_ask_after_upload_returns_answer():
    doc_id = _upload_sample_doc()

    resp = client.post(f"/documents/{doc_id}/ask", json={"question": "QuickSort la gi?"})

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "answer" in data
    assert data["confidence"] in ("high", "low")
    assert len(data["retrieved_chunks"]) >= 1


def test_ask_unknown_doc_returns_404():
    resp = client.post("/documents/unknown-id/ask", json={"question": "x"})
    assert resp.status_code == 404


def test_ask_empty_question_returns_400():
    doc_id = _upload_sample_doc()
    resp = client.post(f"/documents/{doc_id}/ask", json={"question": "   "})
    assert resp.status_code == 400


def test_get_file_returns_pdf_bytes():
    doc_id = _upload_sample_doc()
    resp = client.get(f"/documents/{doc_id}/file")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_get_file_unknown_doc_returns_404():
    resp = client.get("/documents/unknown-id/file")
    assert resp.status_code == 404
