import { useEffect, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

function normalize(s) {
  return (s || "").toLowerCase().replace(/\s+/g, " ").trim();
}

function escapeHtml(s) {
  return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/**
 * Highlight citation trên đúng trang PDF gốc (implementation_plan.md mục 6).
 *
 * Cách làm: nối text của toàn bộ text-item trên trang thành 1 chuỗi (đã chuẩn hoá
 * whitespace, giống cách backend chuẩn hoá ở app/graph/verification.py), tìm vị trí
 * của exact_quote trong chuỗi đó, rồi tô sáng các item trùng vị trí đó qua
 * `customTextRenderer` (API chính thức của react-pdf).
 *
 * Lưu ý quan trọng: `onGetTextSuccess` của react-pdf chỉ bắn đúng 1 lần khi trang
 * load xong text -- KHÔNG bắn lại khi highlightQuote đổi (vd. click sang citation
 * khác trên cùng trang). Vì vậy phải tách 2 việc: (1) lưu lại text từng item khi
 * trang load (onGetTextSuccess, chạy 1 lần/trang), (2) tính lại highlightRange mỗi
 * khi highlightQuote đổi bằng useEffect riêng (chạy lại độc lập với việc trang có
 * load lại hay không).
 *
 * Giới hạn đã biết: tìm bằng substring chính xác (sau chuẩn hoá), không fuzzy như
 * backend (mục 3.1) -- nếu pdf.js tách câu hơi khác pypdf (dùng để tạo exact_quote
 * ở backend), có thể không tìm thấy match và sẽ không highlight gì (an toàn, không
 * highlight sai chỗ).
 */
export default function PdfViewer({ fileUrl, pageNumber, highlightQuote }) {
  const [numPages, setNumPages] = useState(null);
  const [pageItemTexts, setPageItemTexts] = useState([]); // text (đã chuẩn hoá) của từng item trên trang hiện tại
  const [highlightRange, setHighlightRange] = useState(null); // {start, end, offsets}
  const [notFound, setNotFound] = useState(false);

  const targetQuote = normalize(highlightQuote);

  function handleGetTextSuccess(textContent) {
    setPageItemTexts(textContent.items.map((item) => normalize(item.str || "")));
  }

  useEffect(() => {
    if (!targetQuote || pageItemTexts.length === 0) {
      setHighlightRange(null);
      setNotFound(false);
      return;
    }
    let concat = "";
    const offsets = [];
    for (const text of pageItemTexts) {
      const start = concat.length;
      concat += text + " ";
      offsets.push({ start, end: concat.length });
    }
    const idx = concat.indexOf(targetQuote);
    if (idx === -1) {
      setHighlightRange(null);
      setNotFound(true);
    } else {
      setHighlightRange({ start: idx, end: idx + targetQuote.length, offsets });
      setNotFound(false);
    }
  }, [targetQuote, pageItemTexts]);

  function customTextRenderer({ str, itemIndex }) {
    const safe = escapeHtml(str);
    const offset = highlightRange?.offsets?.[itemIndex];
    if (!highlightRange || !offset) return safe;
    if (offset.end > highlightRange.start && offset.start < highlightRange.end) {
      return `<mark>${safe}</mark>`;
    }
    return safe;
  }

  if (!fileUrl) {
    return <div className="pdf-viewer"><p className="subtitle">Upload tài liệu để xem PDF.</p></div>;
  }

  return (
    <div className="pdf-viewer">
      <Document file={fileUrl} onLoadSuccess={(info) => setNumPages(info.numPages)} loading="Đang tải PDF...">
        <Page
          key={pageNumber || 1}
          pageNumber={pageNumber || 1}
          width={360}
          onGetTextSuccess={handleGetTextSuccess}
          customTextRenderer={customTextRenderer}
        />
      </Document>
      <p className="pdf-page-info">
        Trang {pageNumber || 1}{numPages ? ` / ${numPages}` : ""}
        {notFound && " — không tìm thấy đúng câu trích trên trang này (xem giới hạn đã biết trong code)"}
      </p>
    </div>
  );
}
