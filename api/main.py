from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from api.config import settings
from api.database import init_db
from api.events import EventBus


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.event_bus = EventBus()
    os.makedirs(settings.outputs_dir, exist_ok=True)
    os.makedirs(settings.brands_dir, exist_ok=True)
    yield
    # cleanup on shutdown (nothing needed currently)


app = FastAPI(
    title="Motor de Contenido Agéntico",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.dashboard_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated output files
os.makedirs("./outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="./outputs"), name="outputs")

# Routers (imported here to avoid circular imports at module load)
from api.routers import brands, pipelines, outputs, scripts, media, uploads, chat  # noqa: E402

app.include_router(brands.router, prefix="/api/brands", tags=["brands"])
app.include_router(pipelines.router, prefix="/api/pipelines", tags=["pipelines"])
app.include_router(outputs.router, prefix="/api/outputs", tags=["outputs"])
app.include_router(scripts.router, prefix="/api/scripts", tags=["scripts"])
app.include_router(media.router, prefix="/api/media", tags=["media"])
app.include_router(uploads.router, prefix="/api", tags=["uploads"])
app.include_router(chat.router, prefix="/api", tags=["chat"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
