"""
Traffic Video Analytics System — FastAPI Application Entry Point.

This is the main application that wires everything together:
- API routes
- Batch processor initialization
- CORS middleware
- Directory structure creation
- Logging configuration
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router, set_processor
from backend.processing.batch_processor import BatchProcessor

# ── Logging Configuration ──

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent


# ── Directory Structure ──

def ensure_directories():
    """Create the required directory structure."""
    dirs = [
        PROJECT_ROOT / "videos" / "pending",
        PROJECT_ROOT / "videos" / "processing",
        PROJECT_ROOT / "videos" / "completed",
        PROJECT_ROOT / "outputs" / "excel",
        PROJECT_ROOT / "outputs" / "snapshots",
        PROJECT_ROOT / "models",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    logger.info("Directory structure verified")


# ── Application Lifespan ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    logger.info("=" * 60)
    logger.info("Traffic Video Analytics System — Starting Up")
    logger.info("=" * 60)

    ensure_directories()

    # Initialize batch processor
    processor = BatchProcessor()
    set_processor(processor)

    logger.info("System ready — accepting requests")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("Shutting down...")
    processor.shutdown()
    logger.info("Goodbye!")


# ── FastAPI App ──

app = FastAPI(
    title="Traffic Video Analytics System",
    description=(
        "Offline Scalable Traffic Counting System. "
        "Upload traffic videos, draw counting lines, detect & track vehicles, "
        "and export results to Excel."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router)


# ── Health Check ──

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "name": "Traffic Video Analytics System",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    """Health check."""
    return {"status": "healthy"}
