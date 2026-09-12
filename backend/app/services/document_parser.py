"""Parse PDF thành chunk theo trang.

Trang có text layer: dùng pypdf trực tiếp. Trang KHÔNG có text layer (tài liệu
scan) -- render trang thành ảnh bằng pypdfium2 (thư viện Python thuần, không
cần cài binary hệ thống) rồi OCR bằng pytesseract (cần Tesseract cài sẵn trên
máy chạy -- xem Dockerfile cho bản deploy Render).

TODO chưa làm:
- Tokenize câu tiếng Việt khi cần chunk nhỏ hơn theo câu (hiện đang chunk
  nguyên trang, chấp nhận được cho tài liệu giáo trình).
"""

import io

import pypdfium2 as pdfium
import pytesseract
from pypdf import PdfReader

from app.graph.state import Chunk


class DocumentParseError(Exception):
    pass


def _ocr_page(pdf_bytes: bytes, page_index: int) -> str:
    doc = pdfium.PdfDocument(pdf_bytes)
    try:
        page = doc[page_index]
        image = page.render(scale=2).to_pil()
        return (pytesseract.image_to_string(image, lang="vie+eng") or "").strip()
    finally:
        doc.close()


def parse_pdf_to_chunks(pdf_bytes: bytes, doc_id: str, document_name: str) -> list[Chunk]:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as e:  # pypdf raises nhiều loại exception khác nhau tùy lỗi file
        raise DocumentParseError(f"Không đọc được PDF: {e}") from e

    chunks: list[Chunk] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            text = _ocr_page(pdf_bytes, page_number - 1)
        if not text:
            continue  # cả text layer lẫn OCR đều rỗng -- bỏ qua trang này
        chunks.append({
            "chunk_id": f"{doc_id}_p{page_number}",
            "doc_id": doc_id,
            "document_name": document_name,
            "page_number": page_number,
            "text": text,
        })

    if not chunks:
        raise DocumentParseError(
            "Không trích xuất được text nào -- kể cả sau khi thử OCR (có thể ảnh chất lượng quá thấp)."
        )
    return chunks
