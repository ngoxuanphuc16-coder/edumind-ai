import { useState } from "react";
import { askQuestion } from "./api";

const CONFIDENCE_LABEL = {
  high: "✅ Có căn cứ rõ trong tài liệu",
  low: "⚠️ Chưa chắc chắn — kiểm tra lại citation bên dưới",
};

export default function AskPanel({ docId, onCiteClick }) {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState([]); // [{question, ...answerResult}]
  const [asking, setAsking] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  async function handleAsk(e) {
    e.preventDefault();
    if (!question.trim()) return;
    setErrorMsg("");
    setAsking(true);
    try {
      const result = await askQuestion(docId, question);
      setHistory((h) => [...h, { question, ...result }]);
      setQuestion("");
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="ask-panel">
      <h2>Hỏi đáp về tài liệu (Q&A)</h2>
      <p className="subtitle">Hybrid retrieval (Dense + BM25) — độc lập với roadmap, chỉ cần đã upload.</p>

      <form onSubmit={handleAsk} className="ask-form">
        <input
          type="text"
          value={question}
          placeholder="Ví dụ: QuickSort hoạt động như thế nào?"
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button type="submit" disabled={asking || !question.trim()}>
          {asking ? "Đang tìm..." : "Hỏi"}
        </button>
      </form>

      {errorMsg && <p className="error">{errorMsg}</p>}

      <div className="ask-history">
        {history.map((item, i) => (
          <div key={i} className="ask-item">
            <p className="ask-question">❓ {item.question}</p>
            <p className={`confidence ${item.confidence}`}>{CONFIDENCE_LABEL[item.confidence]}</p>
            <p className="ask-answer">{item.answer}</p>
            {item.citations?.map((c, j) => (
              <button key={j} type="button" className="citation" onClick={() => onCiteClick?.(c)}>
                📄 {c.document_name} — trang {c.page_number}: “{c.exact_quote}”
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
