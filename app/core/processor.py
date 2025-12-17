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
# from src.report_splitter import ReportSplitter  # COMMENTED OUT: Report splitting disabled
from src.duplicate_detector import DuplicateDetector
from src.file_manager import FileManager

from app.core.tasks import job_manager
from app.api.models import ProcessingResult, ProcessingStatus, ReportInfo, PageInfo
import base64
from io import BytesIO

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
        "duplicate_pages": 0,
        "unique_pages": 0,
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

        # Check duplicate detection setting
        duplicate_detection_enabled = config.get("duplicate_detection", {}).get("enabled", True)

        # Step 3: Detect and remove duplicate pages (40-70%) - conditional
        requires_user_selection = False
        page_infos = []
        duplicate_map = {}  # Maps duplicate index to original index

        if duplicate_detection_enabled:
            update_progress_sync(45, "Detecting duplicate pages...")
            # Remove 'enabled' key before passing to DuplicateDetector
            dedup_config = {k: v for k, v in config["duplicate_detection"].items() if k != "enabled"}
            duplicate_detector = DuplicateDetector(**dedup_config)

            # Treat each page as a separate "report" for duplicate detection
            page_list = [[page] for page in non_blank_pages]

            # Find duplicates and get unique pages
            unique_indices, duplicate_pairs = duplicate_detector.find_duplicates(page_list)

            # Build duplicate map from duplicate_pairs
            for idx1, idx2, similarity in duplicate_pairs:
                duplicate_map[idx2] = idx1  # idx2 is duplicate of idx1

            stats["unique_pages"] = len(unique_indices)
            stats["duplicate_pages"] = stats["non_blank_pages"] - stats["unique_pages"]
            logger.info(f"Found {stats['duplicate_pages']} duplicate pages")
            update_progress_sync(65, f"Found {stats['duplicate_pages']} duplicate pages")

            # If duplicates found, prepare for user selection
            if stats["duplicate_pages"] > 0:
                requires_user_selection = True
                update_progress_sync(68, "Preparing page previews for user selection...")

                # Save page previews and create page info
                preview_dir = Path(output_dir) / "temp" / f"job_{job_id}"
                preview_dir.mkdir(parents=True, exist_ok=True)

                for idx, page in enumerate(non_blank_pages):
                    is_duplicate = idx not in unique_indices
                    duplicate_of = duplicate_map.get(idx, None)

                    # Save page preview as thumbnail
                    preview_path = preview_dir / f"page_{idx}.jpg"
                    page_resized = page.copy()
                    page_resized.thumbnail((300, 400))  # Thumbnail size
                    page_resized.save(preview_path, "JPEG", quality=85)

                    page_info = PageInfo(
                        page_index=idx,
                        page_number=idx + 1,
                        is_duplicate=is_duplicate,
                        duplicate_of=duplicate_of,
                        preview_url=f"/api/preview/{job_id}/page_{idx}.jpg"
                    )
                    page_infos.append(page_info)

                # Store non_blank_pages for later PDF generation
                import pickle
                pages_cache_path = preview_dir / "pages.pkl"
                with open(pages_cache_path, 'wb') as f:
                    pickle.dump(non_blank_pages, f)

                logger.info(f"Saved {len(page_infos)} page previews for user selection")
                update_progress_sync(70, "Page previews ready for user selection")
            else:
                # No duplicates, proceed normally
                unique_pages = non_blank_pages
                update_progress_sync(70, "No duplicate pages found")
        else:
            update_progress_sync(45, "Skipping duplicate detection (disabled)...")
            logger.info("Duplicate detection disabled - keeping all pages")
            unique_pages = non_blank_pages
            stats["unique_pages"] = len(unique_pages)
            stats["duplicate_pages"] = 0
            update_progress_sync(70, "Duplicate detection skipped")

        # Step 4: Handle result based on whether user selection is required
        if requires_user_selection:
            # User needs to select pages - don't generate PDF yet
            update_progress_sync(100, "Waiting for user to select pages...")

            # Create result with page info for user selection
            result = ProcessingResult(
                job_id=job_id,
                status=ProcessingStatus.COMPLETED,
                input_file=Path(input_path).name,
                total_pages=stats["total_pages"],
                blank_pages=stats["blank_pages"],
                reports_found=1,
                duplicate_reports=stats["duplicate_pages"],
                unique_reports=1,
                reports=[],  # No PDF generated yet
                pages=page_infos,  # Send page information for user selection
                requires_user_selection=True,
                processing_time_seconds=0,
                error=None,
            )

            logger.info(f"Awaiting user selection: {len(page_infos)} pages, {stats['duplicate_pages']} duplicates")
            return result
        else:
            # No duplicates or detection disabled - generate PDF immediately
            update_progress_sync(75, "Saving processed PDF...")
            file_manager = FileManager(output_dir, **config["file_management"])

            # Create metadata for the processed PDF
            metadata = {
                "original_page_indices": list(range(len(unique_pages))),
                "total_pages": stats["total_pages"],
                "blank_pages_removed": stats["blank_pages"],
                "duplicate_pages_removed": stats["duplicate_pages"],
                "processing_mode": "blank_removal_and_deduplication" if duplicate_detection_enabled else "blank_removal_only",
            }

            # Save as single processed PDF
            saved = file_manager.save_report(unique_pages, 1, metadata, original_filename)
            saved_files = [saved]
            stats["saved_files"] = saved_files

            update_progress_sync(90, "Creating processing log...")
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
                    page_count=len(unique_pages),
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
                reports_found=1,  # Always 1 report now
                duplicate_reports=stats["duplicate_pages"],  # Duplicate pages, not reports
                unique_reports=1,  # Always 1 report now
                reports=report_infos,
                pages=None,
                requires_user_selection=False,
                processing_time_seconds=0,  # Will be set by caller
                error=None,
            )

            logger.info(f"Returning processed PDF: {report_infos[0].filename if report_infos else 'None'}")
            logger.info(f"Total pages: {stats['total_pages']}, Blank pages removed: {stats['blank_pages']}, Duplicate pages removed: {stats['duplicate_pages']}, Final pages: {stats['unique_pages']}")
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
            reports_found=1,
            duplicate_reports=stats.get("duplicate_pages", 0),
            unique_reports=1,
            reports=[],
            pages=None,
            requires_user_selection=False,
            processing_time_seconds=0,
            error=str(e),
        )
