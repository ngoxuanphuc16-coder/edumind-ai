# Cần Docker (thay vì native Python buildpack của Render) vì OCR cần cài
# Tesseract -- 1 binary hệ thống, không cài được qua pip/buildCommand thường.
#
# CHƯA test build này trên máy dev (không có Docker cài sẵn) -- verify lại
# ngay sau khi Render build lần đầu, xem log build kỹ nếu deploy fail.

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-vie \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
