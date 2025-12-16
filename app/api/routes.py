"""
API routes for the Medical Report PDF Processor.

Endpoints for file upload, processing, status checking, and report download.
"""

import logging
import os
import asyncio
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from app.api.models import (
    ProcessResponse,
    JobStatusResponse,
    HealthResponse,
    UploadResponse,
    ErrorResponse,
    ListJobsResponse,
    DeleteJobResponse,
    ConfigurationRequest,
    ConfigurationResponse,
    ProcessingStatus,
)
from app.core.tasks import job_manager
from app.core.processor import process_pdf_async
from config.config import get_config, BLANK_DETECTION_CONFIG
import json

logger = logging.getLogger(__name__)

router = APIRouter()

# Constants
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = {".pdf"}
UPLOAD_DIR = Path("input")
OUTPUT_DIR = Path("output")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns application health status and configuration info.
    """
    # Check if Tesseract is available by trying to use pytesseract
    tesseract_available = False
    try:
        import pytesseract
        # Try to get Tesseract version to verify it's actually working
        version = pytesseract.get_tesseract_version()
        tesseract_available = True
        logger.debug(f"Tesseract OCR detected: version {version}")
    except ImportError:
        logger.debug("pytesseract module not installed")
        tesseract_available = False
    except Exception as e:
        logger.debug(f"Tesseract not available: {e}")
        tesseract_available = False

    return HealthResponse(
        status="healthy",
        version="1.1.0",
        tesseract_available=tesseract_available,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a PDF file for processing.

    Args:
        file: PDF file to upload

    Returns:
        Upload confirmation with file details
    """
    # Validate file extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only PDF files are allowed. Got: {file_extension}",
        )

    # Read file and check size
    contents = await file.read()
    file_size = len(contents)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.1f} MB",
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    # Save file
    UPLOAD_DIR.mkdir(exist_ok=True)
    file_path = UPLOAD_DIR / file.filename

    # Handle duplicate filenames
    counter = 1
    original_stem = file_path.stem
    while file_path.exists():
        file_path = UPLOAD_DIR / f"{original_stem}_{counter}{file_extension}"
        counter += 1

    with open(file_path, "wb") as f:
        f.write(contents)

    logger.info(f"File uploaded: {file_path.name} ({file_size / (1024*1024):.2f} MB)")

    return UploadResponse(
        filename=file_path.name,
        size_mb=round(file_size / (1024 * 1024), 2),
        message=f"File '{file_path.name}' uploaded successfully",
    )


@router.post("/process", response_model=ProcessResponse)
async def process_pdf(
    filename: str,
    background_tasks: BackgroundTasks,
    configuration: ConfigurationRequest = None,
):
    """
    Start processing a PDF file.

    Args:
        filename: Name of the uploaded PDF file
        background_tasks: FastAPI background tasks
        configuration: Optional custom configuration

    Returns:
        Job ID and status URL for tracking
    """
    # Validate file exists
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File '{filename}' not found. Please upload the file first.",
        )

    # Create job
    config_dict = configuration.dict(exclude_none=True) if configuration else {}
    job_id = job_manager.create_job(filename, config_dict)

    # Convert configuration to nested dict structure if needed
    processing_config = None
    if configuration:
        # Enforce dependency: If report splitting is disabled, duplicate detection must also be disabled
        enable_duplicate = configuration.enable_duplicate_detection
        if not configuration.enable_report_splitting:
            enable_duplicate = False
            logger.info("Duplicate detection disabled because report splitting is disabled (dependency)")

        processing_config = {
            "pdf": {
                "dpi": configuration.pdf_dpi,
                "image_format": configuration.pdf_image_format,
                "color_space": configuration.pdf_color_space,
            },
            "blank_detection": {
                "variance_threshold": configuration.variance_threshold,
                "edge_threshold": configuration.edge_threshold,
                "white_pixel_ratio": configuration.white_pixel_ratio,
                "use_edge_detection": configuration.use_edge_detection,
            },
            "report_splitting": {
                "enabled": configuration.enable_report_splitting,
                "use_ocr": configuration.use_ocr,
                "ocr_language": configuration.ocr_language,
                "min_confidence": configuration.min_confidence,
            },
            "duplicate_detection": {
                "enabled": enable_duplicate,
                "hash_algorithm": configuration.hash_algorithm,
                "similarity_threshold": configuration.similarity_threshold,
                "hamming_distance_threshold": configuration.hamming_distance_threshold,
            },
            "file_management": {
                "output_format": configuration.output_format,
                "include_metadata": configuration.include_metadata,
            },
        }
        # Remove None values
        processing_config = {k: {kk: vv for kk, vv in v.items() if vv is not None} for k, v in processing_config.items()}

    # Start processing in background
    background_tasks.add_task(
        _process_and_update,
        job_id,
        str(file_path),
        str(OUTPUT_DIR),
        processing_config,
    )

    logger.info(f"Started processing job {job_id} for file: {filename}")

    return ProcessResponse(
        job_id=job_id,
        status=ProcessingStatus.PENDING,
        message=f"Processing started for '{filename}'",
        status_url=f"/api/jobs/{job_id}",
    )


async def _process_and_update(
    job_id: str,
    input_path: str,
    output_dir: str,
    config: dict,
):
    """
    Background task to process PDF and update job status.
    """
    try:
        result = await process_pdf_async(job_id, input_path, output_dir, config)
        await job_manager.complete_job(job_id, result)
    except Exception as e:
        logger.error(f"Error in background processing: {e}", exc_info=True)
        await job_manager.fail_job(job_id, str(e))


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a processing job.

    Args:
        job_id: Job identifier

    Returns:
        Job status and result if completed
    """
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job["progress"],
        current_step=job.get("current_step"),
        result=job.get("result"),
        error=job.get("error"),
        created_at=job["created_at"],
        updated_at=job["updated_at"],
    )


@router.get("/jobs", response_model=ListJobsResponse)
async def list_jobs():
    """
    List all processing jobs.

    Returns:
        List of all jobs with their status
    """
    jobs = job_manager.get_all_jobs()

    job_responses = [
        JobStatusResponse(
            job_id=job["job_id"],
            status=job["status"],
            progress=job["progress"],
            current_step=job.get("current_step"),
            result=job.get("result"),
            error=job.get("error"),
            created_at=job["created_at"],
            updated_at=job["updated_at"],
        )
        for job in jobs
    ]

    return ListJobsResponse(jobs=job_responses, total=len(job_responses))


@router.delete("/jobs/{job_id}", response_model=DeleteJobResponse)
async def delete_job(job_id: str):
    """
    Delete a processing job.

    Args:
        job_id: Job identifier

    Returns:
        Deletion confirmation
    """
    deleted = job_manager.delete_job(job_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return DeleteJobResponse(
        job_id=job_id,
        message=f"Job '{job_id}' deleted successfully",
    )


@router.get("/download/{filename}")
async def download_report(filename: str):
    """
    Download a processed report.

    Args:
        filename: Name of the report file

    Returns:
        File download response
    """
    file_path = OUTPUT_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf",
    )


@router.get("/configuration", response_model=ConfigurationResponse)
async def get_configuration():
    """
    Get the current default configuration.

    Returns:
        Current configuration settings
    """
    config = get_config()

    return ConfigurationResponse(
        configuration=config,
        message="Current default configuration",
    )


@router.get("/configs/list")
async def list_configs():
    """
    List all available configuration presets.

    Returns:
        List of available configs with their status
    """
    from pathlib import Path

    base_dir = Path(__file__).parent.parent.parent
    optimized_path = base_dir / "config" / "optimized_config.json"
    tuned_path = base_dir / "config" / "tuned_config.json"

    configs = [
        {
            "name": "current",
            "label": "Current (Default)",
            "description": "Current default configuration from config.py",
            "available": True,
        },
        {
            "name": "optimized",
            "label": "Optimized",
            "description": "Auto-optimized parameters from sample analysis",
            "available": optimized_path.exists(),
            "path": str(optimized_path.relative_to(base_dir)) if optimized_path.exists() else None,
        },
        {
            "name": "tuned",
            "label": "Tuned",
            "description": "Manually tuned parameters from interactive tool",
            "available": tuned_path.exists(),
            "path": str(tuned_path.relative_to(base_dir)) if tuned_path.exists() else None,
        },
    ]

    return {"configs": configs}


@router.get("/configs/{config_name}")
async def get_config_by_name(config_name: str):
    """
    Get parameters for a specific configuration preset.

    Args:
        config_name: Name of the config (current, optimized, tuned)

    Returns:
        Configuration parameters
    """
    from pathlib import Path

    base_dir = Path(__file__).parent.parent.parent

    if config_name == "current":
        # Return current default config
        return {
            "name": "current",
            "label": "Current (Default)",
            "parameters": {
                "blank_detection": BLANK_DETECTION_CONFIG,
            }
        }

    elif config_name == "optimized":
        optimized_path = base_dir / "config" / "optimized_config.json"
        if not optimized_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Optimized config not found. Run tools/optimize_parameters.py first."
            )

        with open(optimized_path, "r") as f:
            config_data = json.load(f)

        return {
            "name": "optimized",
            "label": "Optimized",
            "parameters": config_data,
            "metadata": config_data.get("optimization_metadata", {})
        }

    elif config_name == "tuned":
        tuned_path = base_dir / "config" / "tuned_config.json"
        if not tuned_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Tuned config not found. Run tools/interactive_tuner.py first."
            )

        with open(tuned_path, "r") as f:
            config_data = json.load(f)

        return {
            "name": "tuned",
            "label": "Tuned",
            "parameters": config_data,
            "metadata": config_data.get("tuning_metadata", {})
        }

    else:
        raise HTTPException(
            status_code=404,
            detail=f"Config '{config_name}' not found. Available: current, optimized, tuned"
        )


@router.websocket("/ws/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time progress updates.

    Args:
        websocket: WebSocket connection
        job_id: Job identifier to track
    """
    await websocket.accept()

    # Register progress callback
    async def send_progress(progress_update):
        try:
            await websocket.send_json(progress_update.dict())
        except Exception as e:
            logger.error(f"Error sending progress update: {e}")

    job_manager.register_progress_callback(job_id, send_progress)

    try:
        # Keep connection alive and listen for disconnect
        while True:
            try:
                data = await websocket.receive_text()
                # Echo back or handle client messages if needed
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for job {job_id}")
                break
    finally:
        job_manager.unregister_progress_callbacks(job_id)
