"""
Pydantic models for API request and response schemas.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ProcessingStatus(str, Enum):
    """Processing job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfigurationRequest(BaseModel):
    """Request model for processing configuration"""
    # PDF settings
    pdf_dpi: Optional[int] = Field(200, description="DPI for PDF to image conversion")
    pdf_image_format: Optional[str] = Field("PNG", description="Image format (PNG/JPEG)")
    pdf_color_space: Optional[str] = Field("RGB", description="Color space (RGB/GRAY)")

    # Blank detection settings
    variance_threshold: Optional[float] = Field(100.0, description="Pixel variance threshold for blank detection")
    edge_threshold: Optional[int] = Field(50, description="Edge count threshold for blank detection")
    white_pixel_ratio: Optional[float] = Field(0.95, description="White pixel ratio for blank detection")
    use_edge_detection: Optional[bool] = Field(True, description="Enable Canny edge detection")

    # Report splitting settings
    enable_report_splitting: Optional[bool] = Field(True, description="Enable report splitting (default: True)")
    use_ocr: Optional[bool] = Field(True, description="Enable OCR for pattern detection")
    ocr_language: Optional[str] = Field("eng", description="Tesseract language code")
    min_confidence: Optional[int] = Field(60, description="Minimum OCR confidence score (0-100)")
    header_keywords: Optional[List[str]] = Field(
        default=None,
        description="Keywords to detect in report headers"
    )

    # Duplicate detection settings
    enable_duplicate_detection: Optional[bool] = Field(True, description="Enable duplicate detection (default: True)")
    hash_algorithm: Optional[str] = Field("phash", description="Hash algorithm (phash/dhash/whash/average_hash)")
    similarity_threshold: Optional[float] = Field(0.95, description="Similarity threshold for duplicates")
    hamming_distance_threshold: Optional[int] = Field(5, description="Hamming distance threshold")

    # File management settings
    output_format: Optional[str] = Field("pdf", description="Output format (pdf/images/both)")
    include_metadata: Optional[bool] = Field(True, description="Include metadata JSON files")


class ProcessRequest(BaseModel):
    """Request model for processing job"""
    filename: str = Field(..., description="Name of the uploaded PDF file")
    configuration: Optional[ConfigurationRequest] = Field(None, description="Optional custom configuration")


class ReportInfo(BaseModel):
    """Information about a processed report"""
    report_id: str = Field(..., description="Unique report identifier")
    filename: str = Field(..., description="Report filename")
    page_count: int = Field(..., description="Number of pages in the report")
    file_size_mb: float = Field(..., description="File size in MB")
    download_url: str = Field(..., description="URL to download the report")


class ProcessingProgress(BaseModel):
    """Processing progress update"""
    job_id: str = Field(..., description="Job identifier")
    status: ProcessingStatus = Field(..., description="Current processing status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    current_step: str = Field(..., description="Description of current step")
    message: Optional[str] = Field(None, description="Additional message or error details")


class ProcessingResult(BaseModel):
    """Final processing result"""
    job_id: str = Field(..., description="Job identifier")
    status: ProcessingStatus = Field(..., description="Final processing status")
    input_file: str = Field(..., description="Input PDF filename")
    total_pages: int = Field(..., description="Total pages in input PDF")
    blank_pages: int = Field(..., description="Number of blank pages removed")
    reports_found: int = Field(..., description="Number of reports identified")
    duplicate_reports: int = Field(..., description="Number of duplicate reports removed")
    unique_reports: int = Field(..., description="Number of unique reports saved")
    reports: List[ReportInfo] = Field(..., description="List of processed reports")
    processing_time_seconds: float = Field(..., description="Total processing time")
    error: Optional[str] = Field(None, description="Error message if processing failed")


class ProcessResponse(BaseModel):
    """Response model for process initiation"""
    job_id: str = Field(..., description="Unique job identifier")
    status: ProcessingStatus = Field(..., description="Initial job status")
    message: str = Field(..., description="Response message")
    status_url: str = Field(..., description="URL to check job status")


class JobStatusResponse(BaseModel):
    """Response model for job status check"""
    job_id: str = Field(..., description="Job identifier")
    status: ProcessingStatus = Field(..., description="Current job status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    current_step: Optional[str] = Field(None, description="Current processing step")
    result: Optional[ProcessingResult] = Field(None, description="Final result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Application version")
    tesseract_available: bool = Field(..., description="Whether Tesseract OCR is available")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class UploadResponse(BaseModel):
    """File upload response"""
    filename: str = Field(..., description="Uploaded filename")
    size_mb: float = Field(..., description="File size in MB")
    message: str = Field(..., description="Upload status message")


class ListJobsResponse(BaseModel):
    """Response model for listing all jobs"""
    jobs: List[JobStatusResponse] = Field(..., description="List of all jobs")
    total: int = Field(..., description="Total number of jobs")


class DeleteJobResponse(BaseModel):
    """Response model for job deletion"""
    job_id: str = Field(..., description="Deleted job identifier")
    message: str = Field(..., description="Deletion status message")


class ConfigurationResponse(BaseModel):
    """Response model for current configuration"""
    configuration: Dict[str, Any] = Field(..., description="Current configuration settings")
    message: str = Field(..., description="Response message")
