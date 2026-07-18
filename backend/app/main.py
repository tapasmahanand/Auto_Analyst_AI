from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .routers import analyses, datasets, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings().ensure_dirs()
    init_db()
    yield


app = FastAPI(title="AutoAnalyst AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router)
app.include_router(analyses.router)
app.include_router(reports.router)


@app.get("/api/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "openai_configured": bool(
            settings.openai_api_key and not settings.openai_api_key.startswith("sk-...")
        ),
        "model": settings.openai_model,
    }
