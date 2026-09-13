# EduMind AI — Khung chương trình (v0.1 scaffold)

Hiện thực hoá `implementation_plan.md` (v2): FastAPI + LangGraph (backend) + React/Vite (frontend),
Qdrant cho vector store, Ollama cho LLM local.

## Trạng thái hiện tại (đã test)

- Backend: 23/23 test pass (`pytest`) -- gồm vòng lặp fact-check (3 nhánh: approved ngay /
  approved sau refine / approved_with_warning), Q&A retrieval (hybrid search, grounding, doc_id
  filter), endpoint phục vụ file PDF gốc, DB bền vững (libsql/Turso), và OCR fallback.
- Đã verify qua HTTP server thật (không chỉ pytest): upload → process → roadmap → file → ask,
  **rồi restart server**, xác nhận tài liệu vẫn truy cập được (đúng mục tiêu "DB thật thay RAM").
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

## DB thật (libsql/Turso) -- thay cho lưu RAM

`app/services/document_store.py` (`SqlDocumentStore`) lưu document/roadmap/**file PDF gốc**
(dạng blob, không chỉ metadata) qua `libsql` -- cùng 1 client code chạy được với file SQLite
local (mặc định, không cần tài khoản) lẫn database Turso từ xa (production).

**Vì sao lưu cả file PDF, không chỉ metadata**: nếu chỉ lưu roadmap mà không lưu file gốc, sau
restart roadmap vẫn còn nhưng bấm "xem PDF gốc" sẽ 404 -- mất tác dụng "hết mất dữ liệu". Router
`/upload` giờ đọc bytes trực tiếp từ `UploadFile`, không ghi ra đĩa nữa (`document_parser.py`
nhận `pdf_bytes`, không nhận path).

**Điểm còn hở đã xử lý**: embedding trong Qdrant vẫn nằm trên ổ đĩa tạm (mất khi Render restart)
dù chunks đã bền vững trong DB. `qa_service.answer_question` kiểm tra `vector_store.count_for_doc`
-- nếu bằng 0 mà đã có chunks, tự embed lại trước khi search (xem
`test_answer_question_reembeds_when_vector_store_lost_chunks`).

**Để bật Turso thật (bắt buộc cho production, không thì vẫn mất dữ liệu như RAM cũ vì Render free
tier có ổ đĩa tạm thời)**:
```bash
# 1. Tạo tài khoản free tại https://turso.tech, tạo 1 database
# 2. Lấy connection URL + auth token (turso CLI hoặc dashboard)
```
Set `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN` trong `backend/.env` (local) hoặc Render dashboard
(production, xem `render.yaml`). Không set gì = chạy file SQLite local, đủ cho dev nhưng vẫn mất
dữ liệu trên Render free tier khi restart.

**Chưa test được với Turso remote thật** (chưa có tài khoản khi viết code này) -- cơ chế
embedded-replica (`sync_url`) dựa theo tài liệu chính thức của `libsql`, cần verify lại khi có
credentials thật.

## OCR cho tài liệu scan

Trang PDF không có text layer → render thành ảnh bằng `pypdfium2` (thư viện Python thuần) → OCR
bằng `pytesseract` (`lang="vie+eng"`). Xem `_ocr_page()` trong `document_parser.py`.

**Cần Tesseract cài trên máy chạy**. `pytest` chỉ mock `pytesseract.image_to_string` (không cần
Tesseract để chạy test suite) -- nhưng OCR **thật** đã được verify: build `backend/Dockerfile`
qua Docker Desktop local, chạy container thật, upload 1 PDF dạng ảnh (không text layer) và xác
nhận Tesseract 5.5.0 (`eng`+`vie`) đọc đúng nội dung qua `/process`. Để dùng OCR thật ngoài
container (vd. chạy uvicorn trực tiếp trên Windows): cài Tesseract cho Windows
(https://github.com/UB-Mannheim/tesseract/wiki) + gói ngôn ngữ `vie`.

**Trên Render**: đổi từ native Python buildpack sang Docker (`backend/Dockerfile`, cài
`tesseract-ocr` + `tesseract-ocr-vie` qua apt) -- xem `render.yaml` (`runtime: docker`). Build sẽ
chậm hơn (5-8 phút thay vì 2-5 phút) do phải tải nhiều gói Python hơn (`libsql`, `pypdfium2`,
`pytesseract`) ngoài phần apt. Đã build + chạy container thành công trên máy dev qua Docker
Desktop (bao gồm test OCR thật) -- rủi ro chính còn lại trên Render là tốc độ mạng CI-time, không
phải lỗi Dockerfile.

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
python -m pytest tests/ -v          # 23 test, chạy bằng mock, không cần Ollama/Turso/Tesseract
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
      document_parser.py      # PDF -> chunks (pypdf + OCR fallback qua pypdfium2/pytesseract)
      document_store.py        # SqlDocumentStore (libsql/Turso) -- bền vững, không còn RAM
    routers/documents.py      # upload / process / roadmap
  tests/
    test_pipeline.py          # Verify graph logic bằng mock (3 kịch bản retry)
    test_api.py                # Health check
frontend/
  src/App.jsx                  # Upload form + hiển thị roadmap/dag_order/quiz
docker-compose.yml              # Qdrant + Ollama server thật (optional, cần Docker)
```

## Còn thiếu

- **Turso remote thật**: code đã viết xong nhưng chưa test với credentials thật (xem mục "DB thật"
  ở trên) -- cần bạn tạo tài khoản Turso rồi verify lại.
- **OCR/Docker**: đã verify thật (build + chạy container + OCR ảnh thật qua Tesseract 5.5.0) trên
  máy dev qua Docker Desktop -- còn lại chỉ là verify build trên chính Render (hạ tầng khác, dù
  Dockerfile giống hệt).
- **Prompt cho Ollama thật**: chưa test với model thật, cần tinh chỉnh khi có kết quả.
- **BM25 tokenize**: chưa có word segmentation tiếng Việt thật (xem TODO trong `hybrid_retrieval.py`).
- **Highlight citation**: match bằng substring chính xác, chưa fuzzy như backend (xem giới hạn đã
  biết ở mục "PDF Viewer + Highlight Citation").
