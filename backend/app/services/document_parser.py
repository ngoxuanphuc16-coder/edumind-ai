"""Parse PDF thành chunk theo trang.

TODO chưa làm (nêu rõ để không lầm tưởng đã xong -- implementation_plan.md mục 7):
- OCR fallback cho tài liệu scan (trang không có text layer hiện bị BỎ QUA,
  không tự OCR). Khi cần, thêm pytesseract + cài Tesseract (gói ngôn ngữ `vie`)
  và gọi ở nhánh `if not text:` bên dưới.
- Tokenize câu tiếng Việt khi cần chunk nhỏ hơn theo câu (hiện đang chunk
  nguyên trang, chấp nhận được cho tài liệu giáo trình).
"""

from pypdf import PdfReader

from app.graph.state import Chunk


class DocumentParseError(Exception):
    pass


def parse_pdf_to_chunks(path: str, doc_id: str, document_name: str) -> list[Chunk]:
    try:
        reader = PdfReader(path)
    except Exception as e:  # pypdf raises nhiều loại exception khác nhau tùy lỗi file
        raise DocumentParseError(f"Không đọc được PDF: {e}") from e

    chunks: list[Chunk] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue  # có thể là trang scan -- xem TODO OCR ở trên
        chunks.append({
            "chunk_id": f"{doc_id}_p{page_number}",
            "doc_id": doc_id,
            "document_name": document_name,
            "page_number": page_number,
            "text": text,
        })

    if not chunks:
        raise DocumentParseError(
            "Không trích xuất được text nào -- có thể toàn bộ tài liệu là bản scan, cần OCR (chưa implement)."
        )
    return chunks
