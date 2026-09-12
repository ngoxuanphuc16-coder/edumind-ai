# Deploy EduMind AI (bản demo public, free tier)

Kiến trúc: backend (FastAPI) trên **Render**, frontend (React/Vite) trên **Vercel**. Cả hai đều
có free tier không cần thẻ tín dụng. LLM dùng **mock** ở bản public (Ollama thật vẫn chỉ chạy
local trên máy bạn -- xem lý do ở phần "Vì sao không deploy Ollama" bên dưới).

**Các bước tạo tài khoản/kết nối GitHub/click deploy trên dashboard là việc bạn tự làm** --
Claude không tự tạo tài khoản hay đăng nhập thay bạn được. Phần chuẩn bị code/cấu hình
(`render.yaml`, biến môi trường, CORS) đã làm sẵn trong repo.

---

## Bước 0: Đẩy code lên GitHub

Bạn cần 1 repo GitHub vì cả Render lẫn Vercel đều deploy bằng cách kết nối tới GitHub.

```bash
cd F:/chuong_trinh_chay/edumind-ai
git init
git add .
git commit -m "Initial commit: EduMind AI scaffold"
```

Sau đó vào https://github.com/new tạo 1 repo trống (đừng tick "Add README"), rồi:

```bash
git remote add origin https://github.com/<username>/<repo-name>.git
git branch -M main
git push -u origin main
```

## Bước 1: Deploy backend lên Render

1. Vào https://render.com, đăng ký/đăng nhập bằng tài khoản GitHub.
2. **New +** → **Blueprint** → chọn repo vừa push. Render tự đọc [render.yaml](render.yaml)
   ở gốc repo và đề xuất tạo service `edumind-ai-backend`.
3. Bấm **Apply** / **Create**. Lần đầu build mất 2-5 phút (`pip install -r requirements.txt`).
4. Sau khi deploy xong, Render cho 1 URL dạng `https://edumind-ai-backend.onrender.com` -- copy
   lại, cần cho bước 2.
5. Kiểm tra: mở `https://<url-render-của-bạn>/health` trên trình duyệt, phải thấy
   `{"status":"ok","llm_provider":"mock"}`.

## Bước 2: Deploy frontend lên Vercel

1. Vào https://vercel.com, đăng nhập bằng GitHub.
2. **Add New** → **Project** → chọn cùng repo.
3. Ở màn hình cấu hình project: **Root Directory** đổi thành `frontend` (quan trọng --
   repo có cả backend lẫn frontend, phải chỉ đúng thư mục). Vercel tự nhận diện Vite.
4. Trước khi bấm Deploy, vào **Environment Variables**, thêm:
   - `VITE_API_BASE_URL` = URL Render ở bước 1 (vd. `https://edumind-ai-backend.onrender.com`)
5. Bấm **Deploy**. Xong sẽ có URL dạng `https://<project>.vercel.app`.

## Bước 3: Nối ngược CORS

Quay lại Render dashboard → service `edumind-ai-backend` → **Environment** → sửa biến
`CORS_ORIGINS` thành đúng URL Vercel ở bước 2 (vd. `https://edumind-ai.vercel.app`, **không**
có dấu `/` ở cuối). Render tự khởi động lại service sau khi lưu (không cần build lại).

## Bước 4: Test bản public

Mở URL Vercel, thử đúng luồng đã test local: upload PDF mẫu → xem roadmap (status sẽ luôn
`approved`/`approved_with_warning` với câu trả lời mock) → hỏi Q&A → click citation xem PDF
highlight. Nếu lỗi CORS trong console trình duyệt, kiểm tra lại `CORS_ORIGINS` ở bước 3 có
khớp CHÍNH XÁC domain Vercel không (kể cả https://).

---

## Giới hạn của bản deploy free tier này (nêu rõ, không giấu)

- **Dữ liệu không bền vững**: `document_store` (RAM) và Qdrant embedded
  (`QDRANT_PATH=/tmp/...`) đều mất khi Render restart service (free tier tự ngủ sau 15 phút
  không hoạt động, hoặc mỗi lần deploy lại) -- upload lại tài liệu là bình thường, không phải bug.
- **Cold start**: request đầu tiên sau khi service "ngủ" có thể mất 30-60s để backend thức dậy.
- **LLM là mock**: roadmap/citation/câu trả lời Q&A trên bản public là dữ liệu giả lập minh hoạ
  luồng hoạt động, không phải AI thật. Muốn AI thật, chạy local theo README.md (đã có Ollama).

## Vì sao không deploy Ollama luôn cho "AI thật" public

Ollama cần tối thiểu vài GB RAM ngay cả với model nhỏ; free tier của Render/Railway/Vercel
thường giới hạn 512MB-1GB, không đủ chạy. Muốn AI thật trên bản public, cần 1 trong 2 hướng
(không nằm trong phạm vi bản demo free này):
- Trả tiền cho 1 VPS/cloud đủ RAM (hoặc GPU) để tự host Ollama.
- Đổi sang gọi API LLM trả phí (OpenAI/Anthropic) thay vì Ollama local -- nhẹ cho server, nhưng
  tốn phí theo request.
