# EduMind AI — Khung chương trình (v0.1 scaffold)

Hiện thực hoá `implementation_plan.md` (v2): FastAPI + LangGraph (backend) + React/Vite (frontend),
Qdrant cho vector store, Ollama cho LLM local.

## Trạng thái hiện tại (đã test)

- Backend: 14/14 test pass (`pytest`) -- gồm vòng lặp fact-check (3 nhánh: approved ngay /
  approved sau refine / approved_with_warning), Q&A retrieval (hybrid search, grounding, doc_id
  filter), và endpoint phục vụ file PDF gốc.
- End-to-end thật qua browser (không chỉ curl):
  1. Upload PDF → embed vào Qdrant ngay lúc upload → chạy graph 6 node → trả roadmap+quiz.
  2. Hỏi đáp (Q&A) về tài liệu vừa upload -- hoạt động ngay sau /upload, độc lập với /process.
  3. Click citation (ở roadmap hoặc Q&A) → PDF viewer nhảy đúng trang, tô sáng đúng câu trích
     (đã verify qua computed style thật trên DOM, không chỉ suy đoán từ code).
- Đang chạy ở chế độ **mock LLM** (`LLM_PROVIDER=mock`) vì máy dev hiện tại **chưa cài Ollama**.
- Máy dev hiện tại **chưa cài Docker** -- Qdrant đang chạy ở chế độ embedded/local (không cần server riêng).

## Tính năng Q&A Retrieval (mục 2, implementation_plan.md)

`POST /documents/{doc_id}/ask` (body `{"question": "..."}`) -- luồng dữ liệu THỨ HAI, tách biệt
khỏi ingestion pipeline (roadmap):

1. **Hybrid search**: dense (cosine similarity qua Qdrant, lọc theo `doc_id`) + BM25 (dựng tại
   chỗ từ chunk của đúng tài liệu đó) → hợp nhất bằng Reciprocal Rank Fusion.
   (`app/services/hybrid_retrieval.py`)
2. **Generate + verify**: LLM trả lời kèm citation, hard-check citation với chunk gốc (dùng lại
   `verify_citations_against_chunks` từ ingestion pipeline) -- tối đa **1 lần retry** (không phải
   3 như ingestion, vì đây là tương tác trực tiếp, cần nhanh). Nếu vẫn không đạt, trả lời kèm
   `confidence: "low"` thay vì tiếp tục loop. (`app/services/qa_service.py`)
3. Frontend: `AskPanel` hiện ngay sau khi upload xong (không cần đợi roadmap xử lý xong).

TODO: tokenize BM25 hiện chỉ lowercase + tách whitespace, chưa có word segmentation tiếng Việt
thật (xem comment trong `hybrid_retrieval.py`).

## PDF Viewer + Highlight Citation (mục 6, implementation_plan.md)

`GET /documents/{doc_id}/file` phục vụ file PDF gốc; frontend dùng `react-pdf` (pdf.js) để render.

Click vào bất kỳ citation nào (roadmap hoặc Q&A) → `PdfViewer` nhảy tới đúng `page_number` và tô
sáng `exact_quote` bằng `<mark>`. Cơ chế (`frontend/src/PdfViewer.jsx`):

1. Nối text của toàn bộ text-item trên trang pdf.js trích ra thành 1 chuỗi (chuẩn hoá whitespace,
   cùng cách backend chuẩn hoá ở `verification.py`).
2. Tìm vị trí `exact_quote` trong chuỗi đó, ánh xạ ngược sang các text-item bị trùng phạm vi.
3. Highlight qua `customTextRenderer` (API chính thức của react-pdf) -- không tự chế DOM.

**Bug đã gặp và sửa**: `onGetTextSuccess` của react-pdf chỉ bắn 1 lần khi trang load xong text,
không bắn lại khi đổi `highlightQuote` (vd. click citation thứ 2 trên cùng trang) -- ban đầu
highlight không hoạt động vì tính toán vị trí nằm trong callback đó. Sửa bằng cách tách: lưu text
từng item khi trang load (1 lần), còn việc tính vị trí highlight chạy trong `useEffect` riêng phụ
thuộc `highlightQuote` (chạy lại mỗi lần đổi, độc lập với việc trang có load lại hay không).

**Giới hạn đã biết**: so khớp bằng substring chính xác (sau chuẩn hoá), không fuzzy như backend
(mục 3.1). Nếu pdf.js tách câu khác với pypdf (dùng để tạo `exact_quote` ở backend), có thể không
tìm thấy match -- khi đó UI hiện dòng "không tìm thấy đúng câu trích trên trang này" thay vì
highlight sai chỗ.

## Cần làm trước khi dùng LLM thật

```bash
# 1. Cài Ollama: https://ollama.com/download
# 2. Pull các model đã cấu hình mặc định trong backend/.env.example
ollama pull qwen2.5:7b        # generator
ollama pull qwen2.5:3b        # fact-checker (khác model với generator, xem mục 3.1 trong implementation_plan.md)
ollama pull nomic-embed-text  # embedding
```

Sau đó trong `backend/.env` (copy từ `.env.example`): đổi `LLM_PROVIDER=ollama`.

**Lưu ý:** prompt trong `app/services/llm_client.py` (`OllamaLLMClient`) là điểm khởi đầu,
gần như chắc chắn cần tinh chỉnh sau khi thấy output thật từ model bạn chọn (đặc biệt với
tiếng Việt) -- chưa test được với LLM thật trong phiên này.

## Chạy backend

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v          # 5 test, chạy bằng mock, không cần Ollama
python -m uvicorn app.main:app --port 8123 --reload
```

API: `POST /documents/upload` (multipart PDF) → `POST /documents/{doc_id}/process` → `GET /documents/{doc_id}/roadmap`.

## Chạy frontend

```bash
cd frontend
npm install
npm run dev
```

Mở `http://localhost:5173`. Backend phải chạy ở `:8123` (CORS đã mở sẵn cho origin này).

## Cấu trúc

```
backend/
  app/
    config.py            # Settings (.env) -- LLM_PROVIDER, Ollama models, Qdrant path
    graph/
      state.py            # StudyState (TypedDict)
      verification.py      # Lớp 1: hard-check citation (fuzzy match, không dùng LLM)
      dag.py                # Cycle detection + topological sort
      nodes.py               # 6 node function (extract_kg, generate_roadmap, fact_checker, build_dag, generate_quiz, finalize)
      pipeline.py              # Lắp StateGraph
    services/
      llm_client.py         # LLMClient protocol + MockLLMClient + OllamaLLMClient
      vector_store.py        # Qdrant wrapper (embedded local mode mặc định)
      document_parser.py      # PDF -> chunks (pypdf; OCR CHƯA implement, xem TODO trong file)
      document_store.py        # Lưu tạm trong RAM -- CHƯA phải DB thật
    routers/documents.py      # upload / process / roadmap
  tests/
    test_pipeline.py          # Verify graph logic bằng mock (3 kịch bản retry)
    test_api.py                # Health check
frontend/
  src/App.jsx                  # Upload form + hiển thị roadmap/dag_order/quiz
docker-compose.yml              # Qdrant + Ollama server thật (optional, cần Docker)
```

## Đã biết còn thiếu (không giả vờ là xong)

- **OCR** cho tài liệu scan: chưa implement (xem TODO trong `document_parser.py`).
- **Persistent DB**: `document_store.py` hiện lưu trong RAM, mất khi restart server.
  Roadmap ở mục "Kế hoạch" cần thay bằng SQLite/Postgres khi làm tiếp.
- **Prompt cho Ollama thật**: chưa test với model thật, cần tinh chỉnh khi có kết quả.
- **BM25 tokenize**: chưa có word segmentation tiếng Việt thật (xem TODO trong `hybrid_retrieval.py`).
- **Highlight citation**: match bằng substring chính xác, chưa fuzzy như backend (xem giới hạn đã
  biết ở mục "PDF Viewer + Highlight Citation").
