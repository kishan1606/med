"""
Async wrapper for the PDF processing pipeline.

Wraps the synchronous processing pipeline to run in background tasks
and provide progress updates.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import time

from config.config import get_config
from src.pdf_processor import PDFProcessor
from src.image_analyzer import ImageAnalyzer
from src.report_splitter import ReportSplitter
from src.duplicate_detector import DuplicateDetector
from src.file_manager import FileManager

from app.core.tasks import job_manager
from app.api.models import ProcessingResult, ProcessingStatus, ReportInfo

logger = logging.getLogger(__name__)


async def process_pdf_async(
    job_id: str,
    input_path: str,
    output_dir: str,
    config: Optional[Dict] = None,
) -> ProcessingResult:
    """
    Process a PDF file asynchronously with progress updates.

    Args:
        job_id: Job identifier for progress tracking
        input_path: Path to input PDF file
        output_dir: Path to output directory
        config: Optional custom configuration

    Returns:
        ProcessingResult with complete processing information
    """
    start_time = time.time()

    # Get default config and merge with custom config
    default_config = get_config()
    if config:
        # Merge custom config
        for key, value in config.items():
            if key in default_config:
                if isinstance(default_config[key], dict) and isinstance(value, dict):
                    default_config[key].update(value)
                else:
                    default_config[key] = value

    processing_config = default_config

    try:
        # Update status to processing
        await job_manager.update_progress(
            job_id, 0, "Starting PDF processing...", ProcessingStatus.PROCESSING
        )

        # Run the processing in a thread pool to avoid blocking
        # Pass the current event loop to the sync function
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            _process_pdf_sync,
            job_id,
            input_path,
            output_dir,
            processing_config,
            loop,  # Pass event loop
        )

        processing_time = time.time() - start_time
        result.processing_time_seconds = processing_time

        return result

    except Exception as e:
        logger.error(f"Error processing PDF in job {job_id}: {e}", exc_info=True)
        await job_manager.fail_job(job_id, str(e))

        # Return failed result
        return ProcessingResult(
            job_id=job_id,
            status=ProcessingStatus.FAILED,
            input_file=Path(input_path).name,
            total_pages=0,
            blank_pages=0,
            reports_found=0,
            duplicate_reports=0,
            unique_reports=0,
            reports=[],
            processing_time_seconds=time.time() - start_time,
            error=str(e),
        )


def _process_pdf_sync(
    job_id: str, input_path: str, output_dir: str, config: Dict, event_loop
) -> ProcessingResult:
    """
    Synchronous processing function (runs in thread pool).

    Args:
        job_id: Job identifier
        input_path: Path to input PDF
        output_dir: Output directory
        config: Configuration dictionary
        event_loop: Event loop from async context for progress updates

    Returns:
        ProcessingResult
    """
    logger.info(f"Starting synchronous processing for job {job_id}")

    # Convert async progress updates to sync by using asyncio
    def update_progress_sync(progress: int, step: str):
        """Helper to update progress synchronously"""
        try:
            # Use the event loop passed from async context
            if event_loop and not event_loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    job_manager.update_progress(job_id, progress, step),
                    event_loop,
                )
            else:
                logger.debug(f"Progress update: {progress}% - {step}")
        except Exception as e:
            # If anything fails, just log
            logger.debug(f"Progress update failed: {e}")

    # Extract original filename without path and extension for use in output filenames
    original_filename = Path(input_path).stem  # Gets filename without extension

    stats = {
        "input_file": input_path,
        "original_filename": original_filename,
        "total_pages": 0,
        "blank_pages": 0,
        "non_blank_pages": 0,
        "reports_found": 0,
        "unique_reports": 0,
        "duplicate_reports": 0,
        "success": False,
        "error": None,
    }

    try:
        # Step 1: Extract pages from PDF (0-20%)
        update_progress_sync(5, "Extracting pages from PDF...")
        pdf_processor = PDFProcessor(**config["pdf"])
        pages = pdf_processor.extract_pages(input_path)
        stats["total_pages"] = len(pages)
        logger.info(f"Extracted {len(pages)} pages")
        update_progress_sync(20, f"Extracted {len(pages)} pages")

        # Step 2: Remove blank pages (20-40%)
        update_progress_sync(25, "Detecting and removing blank pages...")
        image_analyzer = ImageAnalyzer(**config["blank_detection"])
        non_blank_pages, non_blank_indices, metrics = image_analyzer.filter_blank_pages(pages)
        stats["non_blank_pages"] = len(non_blank_pages)
        stats["blank_pages"] = stats["total_pages"] - stats["non_blank_pages"]
        logger.info(f"Removed {stats['blank_pages']} blank pages")
        update_progress_sync(40, f"Removed {stats['blank_pages']} blank pages")

        if not non_blank_pages:
            raise ValueError("No non-blank pages found in the PDF")

        # Enforce dependency: If report splitting is disabled, duplicate detection must be disabled
        report_splitting_enabled = config.get("report_splitting", {}).get("enabled", True)
        duplicate_detection_enabled = config.get("duplicate_detection", {}).get("enabled", True)

        if not report_splitting_enabled:
            duplicate_detection_enabled = False
            logger.info("Duplicate detection disabled because report splitting is disabled (dependency)")

        # Step 3: Split into individual reports (40-60%) - conditional
        if report_splitting_enabled:
            update_progress_sync(45, "Splitting into individual reports...")
            # Remove 'enabled' key before passing to ReportSplitter
            splitting_config = {k: v for k, v in config["report_splitting"].items() if k != "enabled"}
            report_splitter = ReportSplitter(**splitting_config)
            reports = report_splitter.split_reports(non_blank_pages)
            stats["reports_found"] = len(reports)
            logger.info(f"Identified {len(reports)} reports")
            update_progress_sync(60, f"Identified {len(reports)} reports")
        else:
            update_progress_sync(45, "Skipping report splitting (disabled)...")
            update_progress_sync(60, "Skipping duplicate detection (disabled - dependency)...")
            logger.info("Report splitting disabled - treating as single report")
            logger.info("Duplicate detection disabled - dependency")

            # Save single PDF with blank pages removed
            update_progress_sync(80, "Saving PDF with blank pages removed...")
            file_manager = FileManager(output_dir, **config["file_management"])

            # Create metadata for the single cleaned PDF
            metadata = {
                "original_page_indices": list(range(len(non_blank_pages))),
                "total_pages": stats["total_pages"],
                "blank_pages_removed": stats["blank_pages"],
                "processing_mode": "blank_removal_only",
            }

            # Save as single cleaned PDF
            saved = file_manager.save_report(non_blank_pages, 1, metadata, original_filename)
            saved_files = [saved]
            stats["saved_files"] = saved_files
            stats["reports_found"] = 1
            stats["unique_reports"] = 1
            stats["duplicate_reports"] = 0

            update_progress_sync(95, "Creating processing log...")
            file_manager.create_processing_log(stats)

            output_summary = file_manager.get_output_summary()
            stats["output_summary"] = output_summary
            stats["success"] = True

            update_progress_sync(100, "Processing completed successfully!")

            # Build report info
            report_infos = []
            if "pdf" in saved:
                pdf_path = Path(saved["pdf"])
                file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
                report_info = ReportInfo(
                    report_id="report_0001",
                    filename=pdf_path.name,
                    page_count=len(non_blank_pages),
                    file_size_mb=round(file_size_mb, 2),
                    download_url=f"/api/download/{pdf_path.name}",
                )
                report_infos.append(report_info)

            # Create result
            result = ProcessingResult(
                job_id=job_id,
                status=ProcessingStatus.COMPLETED,
                input_file=Path(input_path).name,
                total_pages=stats["total_pages"],
                blank_pages=stats["blank_pages"],
                reports_found=stats["reports_found"],
                duplicate_reports=stats["duplicate_reports"],
                unique_reports=stats["unique_reports"],
                reports=report_infos,
                processing_time_seconds=0,  # Will be set by caller
                error=None,
            )

            logger.info(f"[Blank Removal Only] Returning {len(report_infos)} report(s)")
            logger.info(f"[Blank Removal Only] Report files: {[r.filename for r in report_infos]}")
            return result

        # Step 4: Detect and remove duplicates (60-80%) - conditional
        if duplicate_detection_enabled:
            update_progress_sync(65, "Detecting duplicate reports...")
            # Remove 'enabled' key before passing to DuplicateDetector
            dedup_config = {k: v for k, v in config["duplicate_detection"].items() if k != "enabled"}
            duplicate_detector = DuplicateDetector(**dedup_config)
            report_pages_list = [report.pages for report in reports]
            unique_indices, duplicate_pairs = duplicate_detector.find_duplicates(report_pages_list)
            unique_reports = [report_pages_list[i] for i in unique_indices]
            stats["unique_reports"] = len(unique_reports)
            stats["duplicate_reports"] = stats["reports_found"] - stats["unique_reports"]
            logger.info(f"Found {stats['duplicate_reports']} duplicates")
            update_progress_sync(80, f"Found {stats['duplicate_reports']} duplicates")
        else:
            update_progress_sync(65, "Skipping duplicate detection (disabled)...")
            logger.info("Duplicate detection disabled - keeping all reports")

            # Save all split reports without deduplication
            update_progress_sync(80, "Saving split reports (with duplicates)...")
            file_manager = FileManager(output_dir, **config["file_management"])

            # Save all reports
            saved_files = []
            for idx, report in enumerate(reports):
                progress = 80 + int((idx + 1) / len(reports) * 15)
                update_progress_sync(progress, f"Saving report {idx + 1}/{len(reports)}...")
                metadata = {
                    "original_page_indices": report.page_indices,
                    "report_number": idx + 1,
                    "total_reports": len(reports),
                    "processing_mode": "split_without_dedup",
                    **report.metadata,
                }
                saved = file_manager.save_report(report.pages, idx + 1, metadata, original_filename)
                saved_files.append(saved)

            stats["saved_files"] = saved_files
            stats["unique_reports"] = len(reports)
            stats["duplicate_reports"] = 0

            update_progress_sync(95, "Creating processing log...")
            file_manager.create_processing_log(stats)

            output_summary = file_manager.get_output_summary()
            stats["output_summary"] = output_summary
            stats["success"] = True

            update_progress_sync(100, "Processing completed successfully!")

            # Build report info list
            report_infos = []
            for idx, saved in enumerate(saved_files):
                if "pdf" in saved:
                    pdf_path = Path(saved["pdf"])
                    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
                    report_info = ReportInfo(
                        report_id=f"report_{idx + 1:04d}",
                        filename=pdf_path.name,
                        page_count=len(reports[idx].pages),
                        file_size_mb=round(file_size_mb, 2),
                        download_url=f"/api/download/{pdf_path.name}",
                    )
                    report_infos.append(report_info)

            # Create result
            result = ProcessingResult(
                job_id=job_id,
                status=ProcessingStatus.COMPLETED,
                input_file=Path(input_path).name,
                total_pages=stats["total_pages"],
                blank_pages=stats["blank_pages"],
                reports_found=stats["reports_found"],
                duplicate_reports=stats["duplicate_reports"],
                unique_reports=stats["unique_reports"],
                reports=report_infos,
                processing_time_seconds=0,  # Will be set by caller
                error=None,
            )

            logger.info(f"[Split Without Dedup] Returning {len(report_infos)} report(s)")
            logger.info(f"[Split Without Dedup] Report files: {[r.filename for r in report_infos]}")
            return result

        # Step 5: Save processed reports (80-100%) - Full pipeline with deduplication
        update_progress_sync(85, "Saving unique processed reports...")
        file_manager = FileManager(output_dir, **config["file_management"])

        # Create metadata for each report
        reports_metadata = []
        for idx, report_idx in enumerate(unique_indices):
            original_report = reports[report_idx]
            metadata = {
                "original_page_indices": original_report.page_indices,
                "report_number": idx + 1,
                "total_unique_reports": len(unique_reports),
                "processing_mode": "full_pipeline",
                **original_report.metadata,
            }
            reports_metadata.append(metadata)

        # Save all reports
        saved_files = []
        for idx, (pages, metadata) in enumerate(zip(unique_reports, reports_metadata)):
            progress = 85 + int((idx + 1) / len(unique_reports) * 10)
            update_progress_sync(
                progress, f"Saving report {idx + 1}/{len(unique_reports)}..."
            )
            saved = file_manager.save_report(pages, idx + 1, metadata, original_filename)
            saved_files.append(saved)

        update_progress_sync(95, "Creating processing log...")
        file_manager.create_processing_log(stats)

        output_summary = file_manager.get_output_summary()
        stats["output_summary"] = output_summary
        stats["success"] = True

        update_progress_sync(100, "Processing completed successfully!")

        # Build report info list
        report_infos = []
        for idx, saved in enumerate(saved_files):
            if "pdf" in saved:
                pdf_path = Path(saved["pdf"])
                file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
                report_info = ReportInfo(
                    report_id=f"report_{idx + 1:04d}",
                    filename=pdf_path.name,
                    page_count=len(unique_reports[idx]),
                    file_size_mb=round(file_size_mb, 2),
                    download_url=f"/api/download/{pdf_path.name}",
                )
                report_infos.append(report_info)

        # Create result
        result = ProcessingResult(
            job_id=job_id,
            status=ProcessingStatus.COMPLETED,
            input_file=Path(input_path).name,
            total_pages=stats["total_pages"],
            blank_pages=stats["blank_pages"],
            reports_found=stats["reports_found"],
            duplicate_reports=stats["duplicate_reports"],
            unique_reports=stats["unique_reports"],
            reports=report_infos,
            processing_time_seconds=0,  # Will be set by caller
            error=None,
        )

        logger.info(f"[Full Pipeline] Returning {len(report_infos)} report(s)")
        logger.info(f"[Full Pipeline] Report files: {[r.filename for r in report_infos]}")
        return result

    except Exception as e:
        logger.error(f"Error in synchronous processing: {e}", exc_info=True)
        stats["error"] = str(e)
        stats["success"] = False

        # Return failed result
        return ProcessingResult(
            job_id=job_id,
            status=ProcessingStatus.FAILED,
            input_file=Path(input_path).name,
            total_pages=stats.get("total_pages", 0),
            blank_pages=stats.get("blank_pages", 0),
            reports_found=stats.get("reports_found", 0),
            duplicate_reports=stats.get("duplicate_reports", 0),
            unique_reports=stats.get("unique_reports", 0),
            reports=[],
            processing_time_seconds=0,
            error=str(e),
        )
