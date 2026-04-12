"""
main.py — FastAPI application entrypoint.

Startup/shutdown lifecycle:
  • DB tables created on startup
  • File watcher started/stopped cleanly
  • CORS enabled for Electron renderer (localhost)
"""

from __future__ import annotations

import asyncio
import logging
import logging.config
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from backend.api.routes import logs, organize, rules, scan
from backend.config import API_HOST, API_PORT, API_RELOAD, LOG_FORMAT, LOG_LEVEL
from backend.core.watcher import FileWatcher
from backend.database.connection import init_db

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async context manager for startup/shutdown."""
    logger.info("Smart File Organizer AI — Starting up")
    await init_db()

    # Global file watcher (paths added via /watcher API or config)
    watcher = FileWatcher(handler=lambda evt: logger.debug("FS event: %s", evt))
    app.state.watcher = watcher

    yield  # App is running

    logger.info("Shutting down...")
    watcher.stop()
    logger.info("Bye.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Smart File Organizer AI",
    description="High-performance file organization engine with REST + WebSocket API.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS — allow Electron renderer (file:// and localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compress responses > 1 KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(scan.router, prefix="/api")
app.include_router(organize.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(logs.router, prefix="/api")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "Smart File Organizer AI"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD,
        log_level=LOG_LEVEL.lower(),
    )
