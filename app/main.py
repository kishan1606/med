"""
Medical Report PDF Processor - FastAPI Web Application

Main application entry point for the FastAPI web interface.
"""

import sys
from pathlib import Path

# Add parent directory to path to allow imports when running directly
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import __version__
from app.api import routes
from app.core.tasks import cleanup_task
import asyncio

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting Medical Report PDF Processor API")
    logger.info(f"Version: {__version__}")

    # Ensure directories exist
    Path("input").mkdir(exist_ok=True)
    Path("output").mkdir(exist_ok=True)
    Path("temp").mkdir(exist_ok=True)

    # Start background cleanup task
    cleanup_task_handle = asyncio.create_task(cleanup_task())

    logger.info("API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down API")
    cleanup_task_handle.cancel()
    try:
        await cleanup_task_handle
    except asyncio.CancelledError:
        pass
    logger.info("API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Medical Report PDF Processor",
    description="API for processing scanned medical report PDFs - extract, split, deduplicate, and save individual reports",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(routes.router, prefix="/api", tags=["API"])

# Mount static files for frontend
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """
    Serve the main web UI.
    """
    static_index = Path(__file__).parent / "static" / "index.html"
    if static_index.exists():
        return FileResponse(static_index)
    else:
        return {
            "message": "Medical Report PDF Processor API",
            "version": __version__,
            "docs": "/docs",
            "api_endpoints": {
                "health": "/api/health",
                "upload": "/api/upload",
                "process": "/api/process",
                "status": "/api/jobs/{job_id}",
                "download": "/api/download/{filename}",
                "list_jobs": "/api/jobs",
            },
        }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    import os
    from config.config import TESSERACT_CMD

    tesseract_available = os.path.exists(TESSERACT_CMD)

    return {
        "status": "healthy",
        "version": __version__,
        "tesseract_available": tesseract_available,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
