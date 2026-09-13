# Cần Docker (thay vì native Python buildpack của Render) vì OCR cần cài
# Tesseract -- 1 binary hệ thống, không cài được qua pip/buildCommand thường.

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-vie \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# --timeout + --retries: mặc định pip không có giới hạn thời gian tổng, nên nếu 1
# kết nối tới PyPI bị treo giữa chừng (gặp thật khi build lần đầu trên máy dev --
# mất >40 phút không nhúc nhích ở gói numpy), nó chờ vô thời hạn thay vì bỏ và thử
# lại. Ép timeout ngắn + retry nhiều lần để tự phục hồi khi gặp kết nối chập chờn.
RUN pip install --no-cache-dir --timeout 30 --retries 10 -r requirements.txt

COPY . .

CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
