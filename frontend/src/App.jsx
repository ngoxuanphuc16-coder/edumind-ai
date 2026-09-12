import { useState } from "react";
import { uploadDocument, processDocument, BASE_URL } from "./api";
import AskPanel from "./AskPanel";
import PdfViewer from "./PdfViewer";
import RoadmapGraph from "./RoadmapGraph";
import "./App.css";

const STATUS_LABEL = {
  approved: "✅ Đã kiểm chứng đầy đủ",
  approved_with_warning: "⚠️ Chưa kiểm chứng đầy đủ sau tối đa số lượt thử — xem lại citation bên dưới",
};

function CitationButton({ citation, onSelect }) {
  return (
    <button type="button" className="citation" onClick={() => onSelect(citation)}>
      📄 {citation.document_name} — trang {citation.page_number}: “{citation.exact_quote}”
    </button>
  );
}

export default function App() {
  const [file, setFile] = useState(null);
  const [stage, setStage] = useState("idle"); // idle | uploading | processing | done | error
  const [result, setResult] = useState(null);
  const [docId, setDocId] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [selectedCitation, setSelectedCitation] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;
    setErrorMsg("");
    setResult(null);
    setDocId(null);
    setSelectedCitation(null);
    try {
      setStage("uploading");
      const upload = await uploadDocument(file);
      setDocId(upload.doc_id); // chunk đã embed vào Qdrant ngay ở /upload -> Q&A dùng được từ đây,
      setStage("processing");   // không cần đợi /process (vốn chỉ để sinh roadmap) xong.
      const processed = await processDocument(upload.doc_id);
      setResult(processed);
      setStage("done");
    } catch (err) {
      setErrorMsg(err.message);
      setStage("error");
    }
  }

  const fileUrl = docId ? `${BASE_URL}/documents/${docId}/file` : null;

  return (
    <div className="layout">
      <div className="main-column">
        <span className="eyebrow">LangGraph · Anti-Hallucination Pipeline</span>
        <h1 className="title">EduMind AI</h1>
        <p className="subtitle">Upload PDF → sinh roadmap có trích dẫn, qua vòng lặp fact-check (LangGraph).</p>

        <form onSubmit={handleSubmit} className="upload-form">
          <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files[0])} />
          <button type="submit" disabled={!file || stage === "uploading" || stage === "processing"}>
            {stage === "uploading" ? "Đang upload..." : stage === "processing" ? "Đang xử lý (fact-check loop)..." : "Tạo roadmap"}
          </button>
        </form>

        {errorMsg && <p className="error">{errorMsg}</p>}

        {docId && <AskPanel docId={docId} onCiteClick={setSelectedCitation} />}

        {result && (
          <div className="result">
            <p className={`status ${result.verification_status}`}>
              {STATUS_LABEL[result.verification_status]} (retry_count={result.retry_count})
            </p>

            <h2>Roadmap</h2>
            <p className="subtitle">Click 1 node để xem trích dẫn + nhảy tới trang PDF tương ứng.</p>
            <RoadmapGraph
              roadmap={result.roadmap}
              edges={result.graph_edges}
              onNodeSelect={setSelectedCitation}
            />

            <h2 className="section-gap">Chi tiết trích dẫn</h2>
            <ul>
              {result.roadmap.map((node) => (
                <li key={node.node_id}>
                  <strong>{node.title}</strong>
                  {node.citations?.map((c, i) => (
                    <CitationButton key={i} citation={c} onSelect={setSelectedCitation} />
                  ))}
                </li>
              ))}
            </ul>

            <h2>Quiz</h2>
            <ul>
              {result.quiz.map((q, i) => <li key={i}>{q.question}</li>)}
            </ul>
          </div>
        )}
      </div>

      <div className="pdf-column">
        <div className="pdf-column-header">
          <span className="dots"><span /><span /><span /></span>
          <span className="label">tai_lieu_goc.pdf</span>
        </div>
        <div className="pdf-column-body">
          <h2>Tài liệu gốc</h2>
          <p className="subtitle">Click vào 1 citation để nhảy tới đúng trang + tô sáng đoạn trích.</p>
          <PdfViewer
            fileUrl={fileUrl}
            pageNumber={selectedCitation?.page_number}
            highlightQuote={selectedCitation?.exact_quote}
          />
        </div>
      </div>
    </div>
  );
}
