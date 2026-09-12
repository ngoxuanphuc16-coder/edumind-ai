import base64
from unittest.mock import patch

import pytest

from app.services.document_parser import DocumentParseError, parse_pdf_to_chunks

# PDF 1 trang có text layer bình thường (tái dùng từ các test khác trong repo).
_TEXT_PDF_B64 = (
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

# PDF 1 trang KHÔNG có text layer (chỉ vẽ 1 hình chữ nhật) -- mô phỏng tài liệu scan.
_NO_TEXT_PDF_B64 = (
    "JVBERi0xLjMKJenr8b8KMSAwIG9iago8PAovQ291bnQgMQovS2lkcyBbMyAwIFJdCi9NZWRpYUJveCBbMCAwIDU5NS4yOCA4NDEuODld"
    "Ci9UeXBlIC9QYWdlcwo+PgplbmRvYmoKMiAwIG9iago8PAovT3BlbkFjdGlvbiBbMyAwIFIgL0ZpdEggbnVsbF0KL1BhZ2VMYXlvdXQg"
    "L09uZUNvbHVtbgovUGFnZXMgMSAwIFIKL1R5cGUgL0NhdGFsb2cKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL0NvbnRlbnRzIDQgMCBSCi9Q"
    "YXJlbnQgMSAwIFIKL1Jlc291cmNlcyA1IDAgUgovVHlwZSAvUGFnZQo+PgplbmRvYmoKNCAwIG9iago8PAovRmlsdGVyIC9GbGF0ZURl"
    "Y29kZQovTGVuZ3RoIDQ2Cj4+CnN0cmVhbQp4nDNS8OIy0DM1VyjnMrLQMzZVsDA01jM1UTA0MdQzN1bQhdJFqQrBXAC8RgiiCmVuZHN0"
    "cmVhbQplbmRvYmoKNSAwIG9iago8PAovUHJvY1NldCBbL1BERiAvVGV4dCAvSW1hZ2VCIC9JbWFnZUMgL0ltYWdlSV0KPj4KZW5kb2Jq"
    "CjYgMCBvYmoKPDwKL0NyZWF0aW9uRGF0ZSAoRDoyMDI2MDkxMjE0NDMyMlopCj4+CmVuZG9iagp4cmVmCjAgNwowMDAwMDAwMDAwIDY1"
    "NTM1IGYgCjAwMDAwMDAwMTUgMDAwMDAgbiAKMDAwMDAwMDEwMiAwMDAwMCBuIAowMDAwMDAwMjA1IDAwMDAwIG4gCjAwMDAwMDAyODUg"
    "MDAwMDAgbiAKMDAwMDAwMDQwMiAwMDAwMCBuIAowMDAwMDAwNDY5IDAwMDAwIG4gCnRyYWlsZXIKPDwKL1NpemUgNwovUm9vdCAyIDAg"
    "UgovSW5mbyA2IDAgUgovSUQgWzw0RjlGOTZBMkY0MEZBOTAyRUM1NEE2RjA0MDQ3RUQ0Qz48NEY5Rjk2QTJGNDBGQTkwMkVDNTRBNkYw"
    "NDA0N0VENEM+XQo+PgpzdGFydHhyZWYKNTI0CiUlRU9GCg=="
)


def test_parse_pdf_extracts_text_from_normal_page():
    pdf_bytes = base64.b64decode(_TEXT_PDF_B64)
    chunks = parse_pdf_to_chunks(pdf_bytes, doc_id="d1", document_name="doc.pdf")
    assert len(chunks) == 1
    assert "QuickSort" in chunks[0]["text"]


def test_parse_pdf_ocr_fallback_for_scanned_page():
    pdf_bytes = base64.b64decode(_NO_TEXT_PDF_B64)
    with patch("app.services.document_parser.pytesseract.image_to_string", return_value="Van ban tu OCR"):
        chunks = parse_pdf_to_chunks(pdf_bytes, doc_id="d1", document_name="scan.pdf")
    assert len(chunks) == 1
    assert chunks[0]["text"] == "Van ban tu OCR"
    assert chunks[0]["page_number"] == 1


def test_parse_pdf_raises_when_ocr_also_returns_empty():
    pdf_bytes = base64.b64decode(_NO_TEXT_PDF_B64)
    with patch("app.services.document_parser.pytesseract.image_to_string", return_value="   "):
        with pytest.raises(DocumentParseError):
            parse_pdf_to_chunks(pdf_bytes, doc_id="d1", document_name="scan.pdf")
