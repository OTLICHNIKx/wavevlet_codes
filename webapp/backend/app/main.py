from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import configs, experiments, health, mc_stats, plots
from app.db.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Wavelet/BCH Research API",
    version="0.1.0",
    lifespan=lifespan,
)


def _cors_origins() -> list[str]:
    """Origin-разрешённые источники: env, иначе localhost-дефолты."""
    raw = os.environ.get("BACKEND_CORS_ORIGINS", "")
    if raw.strip():
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return ["http://localhost:3000", "http://127.0.0.1:3000"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(configs.router)
app.include_router(experiments.router)
app.include_router(plots.router)
app.include_router(mc_stats.router)
