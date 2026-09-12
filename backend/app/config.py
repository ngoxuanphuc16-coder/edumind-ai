from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # "mock" chạy được ngay không cần cài gì thêm (dùng để dev/test).
    # Đổi sang "ollama" sau khi đã cài Ollama + pull model (xem README).
    llm_provider: Literal["mock", "ollama"] = "mock"

    ollama_base_url: str = "http://localhost:11434"
    ollama_generator_model: str = "qwen2.5:7b"
    ollama_checker_model: str = "qwen2.5:3b"       # model rẻ hơn cho fact-checker, tách khỏi model sinh roadmap
    ollama_embedding_model: str = "nomic-embed-text"

    # Qdrant local/embedded mode (path) mặc định -- KHÔNG cần docker/server riêng.
    # Đặt qdrant_url để chuyển sang Qdrant server thật (vd. chạy qua docker-compose.yml).
    qdrant_path: str = "./data/qdrant_local"
    qdrant_url: Optional[str] = None
    qdrant_collection: str = "edumind_chunks"
    qdrant_vector_size: int = 768  # khớp với nomic-embed-text; đổi nếu dùng embedding model khác

    max_retries: int = 3
    faithfulness_threshold: float = 0.85
    citation_match_threshold: float = 90.0

    upload_dir: str = "./data/uploads"

    # Danh sách origin được phép gọi API, cách nhau bởi dấu phẩy. Mặc định chỉ cho
    # Vite dev server local; khi deploy public, set biến môi trường CORS_ORIGINS
    # thành URL frontend thật (vd. https://edumind-ai.vercel.app).
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
