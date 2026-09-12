from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import documents, health, qa

app = FastAPI(title="EduMind AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,        # khớp chính xác (vd. custom domain, localhost dev)
    allow_origin_regex=settings.cors_origin_regex,   # khớp mọi *.vercel.app của project (URL đổi mỗi lần deploy)
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(qa.router)
