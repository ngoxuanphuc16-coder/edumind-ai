"""Ép test luôn hermetic, bất kể backend/.env của máy dev đang set gì (vd.
LLM_PROVIDER=ollama để bạn test local với Ollama thật) -- set env var THẬT
(ưu tiên cao hơn .env theo pydantic-settings) trước khi bất kỳ test module nào
import app.config, để tránh test vô tình gọi ra Ollama/Turso thật rồi timeout.

Bug đã gặp: test_ask_after_upload_returns_answer từng timeout httpx.ReadTimeout
vì đọc nhầm LLM_PROVIDER=ollama từ .env, cố gọi http://localhost:11434 (không
chạy trong môi trường test)."""

import os

os.environ["LLM_PROVIDER"] = "mock"
os.environ.pop("TURSO_DATABASE_URL", None)
os.environ.pop("TURSO_AUTH_TOKEN", None)
