"""
Medical Report PDF Processor - Main Entry Point

This script orchestrates the entire processing pipeline:
1. Extract pages from PDF
2. Remove blank pages
3. Split into individual reports
4. Detect and remove duplicates
5. Save processed reports
"""

import logging
import argparse
import sys
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# Import configuration
from config.config import get_config, ensure_directories

# Import processing modules
from src.pdf_processor import PDFProcessor
from src.image_analyzer import ImageAnalyzer
from src.report_splitter import ReportSplitter
from src.duplicate_detector import DuplicateDetector
from src.file_manager import FileManager


def setup_logging(config: dict):
    """
    Set up logging configuration.

    Args:
        config: Configuration dictionary
    """
    log_config = config["logging"]

    # Create formatters and handlers
    formatter = logging.Formatter(log_config["format"])

    # File handler
    file_handler = logging.FileHandler(log_config["file"])
    file_handler.setFormatter(formatter)

    handlers = [file_handler]

    # Console handler
    if log_config["console"]:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_config["level"]),
        handlers=handlers,
    )


def process_pdf(input_path: str, output_dir: str, config: dict) -> dict:
    """
    Process a single PDF file through the entire pipeline.

    Args:
        input_path: Path to input PDF file
        output_dir: Path to output directory
        config: Configuration dictionary

    Returns:
        Dictionary containing processing statistics
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info(f"Starting PDF processing: {input_path}")
    logger.info("=" * 80)

    # Extract original filename without path and extension for use in output filenames
    original_filename = Path(input_path).stem  # Gets filename without extension

    stats = {
        "input_file": input_path,
        "original_filename": original_filename,
        "start_time": datetime.now().isoformat(),
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
        # Step 1: Extract pages from PDF
        logger.info("Step 1/5: Extracting pages from PDF...")
        pdf_processor = PDFProcessor(**config["pdf"])
        pages = pdf_processor.extract_pages(input_path)
        stats["total_pages"] = len(pages)
        logger.info(f"Extracted {len(pages)} pages")

        # Step 2: Remove blank pages
        logger.info("Step 2/5: Detecting and removing blank pages...")
        image_analyzer = ImageAnalyzer(**config["blank_detection"])
        non_blank_pages, non_blank_indices, metrics = image_analyzer.filter_blank_pages(pages)
        stats["non_blank_pages"] = len(non_blank_pages)
        stats["blank_pages"] = stats["total_pages"] - stats["non_blank_pages"]
        logger.info(
            f"Removed {stats['blank_pages']} blank pages, "
            f"{stats['non_blank_pages']} pages remaining"
        )

        # Check if any pages remain
        if not non_blank_pages:
            logger.warning("No non-blank pages found. Nothing to process.")
            stats["error"] = "No non-blank pages found"
            return stats

        # Enforce dependency: If report splitting is disabled, duplicate detection must be disabled
        report_splitting_enabled = config.get("report_splitting", {}).get("enabled", True)
        duplicate_detection_enabled = config.get("duplicate_detection", {}).get("enabled", True)

        if not report_splitting_enabled:
            duplicate_detection_enabled = False
            logger.info("Duplicate detection disabled because report splitting is disabled (dependency)")

        # Step 3: Split into individual reports (conditional)
        if report_splitting_enabled:
            logger.info("Step 3/5: Splitting into individual reports...")
            # Remove 'enabled' key before passing to ReportSplitter
            splitting_config = {k: v for k, v in config["report_splitting"].items() if k != "enabled"}
            report_splitter = ReportSplitter(**splitting_config)
            reports = report_splitter.split_reports(non_blank_pages)
            stats["reports_found"] = len(reports)
            logger.info(f"Identified {len(reports)} reports")
        else:
            logger.info("Step 3/5: Skipping report splitting (disabled)")
            logger.info("Step 4/5: Skipping duplicate detection (disabled - dependency)")

            # Save single PDF with blank pages removed
            logger.info("Step 5/5: Saving PDF with blank pages removed...")
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

            # Create processing log
            file_manager.create_processing_log(stats)
            output_summary = file_manager.get_output_summary()
            stats["output_summary"] = output_summary
            stats["success"] = True
            stats["end_time"] = datetime.now().isoformat()

            logger.info("Blank pages removed and PDF saved")
            logger.info(f"Output directory: {output_dir}")
            return stats

        # Step 4: Detect and remove duplicates (conditional)
        if duplicate_detection_enabled:
            logger.info("Step 4/5: Detecting duplicate reports...")
            # Remove 'enabled' key before passing to DuplicateDetector
            dedup_config = {k: v for k, v in config["duplicate_detection"].items() if k != "enabled"}
            duplicate_detector = DuplicateDetector(**dedup_config)

            # Convert Report objects to lists of pages
            report_pages_list = [report.pages for report in reports]

            # Find duplicates and get unique reports
            unique_indices, duplicate_pairs = duplicate_detector.find_duplicates(report_pages_list)
            unique_reports = [report_pages_list[i] for i in unique_indices]

            stats["unique_reports"] = len(unique_reports)
            stats["duplicate_reports"] = stats["reports_found"] - stats["unique_reports"]
            logger.info(
                f"Found {stats['duplicate_reports']} duplicates, "
                f"{stats['unique_reports']} unique reports"
            )
        else:
            logger.info("Step 4/5: Skipping duplicate detection (disabled)")

            # Save all split reports without deduplication
            logger.info("Step 5/5: Saving split reports (with duplicates)...")
            file_manager = FileManager(output_dir, **config["file_management"])

            # Save all reports
            report_pages_list = [report.pages for report in reports]
            saved_files = []
            for idx, report in enumerate(reports):
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

            # Create processing log
            file_manager.create_processing_log(stats)
            output_summary = file_manager.get_output_summary()
            stats["output_summary"] = output_summary
            stats["success"] = True
            stats["end_time"] = datetime.now().isoformat()

            logger.info(f"Saved {len(reports)} split reports (duplicates not removed)")
            logger.info(f"Output directory: {output_dir}")
            return stats

        # Step 5: Save processed reports (full pipeline with deduplication)
        logger.info("Step 5/5: Saving unique processed reports...")
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

        # Save all reports with progress bar
        logger.info(f"Saving {len(unique_reports)} reports to {output_dir}")
        saved_files = []
        for idx, (pages, metadata) in enumerate(
            tqdm(
                zip(unique_reports, reports_metadata),
                total=len(unique_reports),
                desc="Saving reports",
            )
        ):
            saved = file_manager.save_report(pages, idx + 1, metadata, original_filename)
            saved_files.append(saved)

        stats["saved_files"] = saved_files

        # Create processing log
        file_manager.create_processing_log(stats)

        # Get output summary
        output_summary = file_manager.get_output_summary()
        stats["output_summary"] = output_summary

        stats["success"] = True
        stats["end_time"] = datetime.now().isoformat()

        logger.info("=" * 80)
        logger.info("Processing completed successfully!")
        logger.info(f"Total pages processed: {stats['total_pages']}")
        logger.info(f"Blank pages removed: {stats['blank_pages']}")
        logger.info(f"Reports identified: {stats['reports_found']}")
        logger.info(f"Duplicate reports: {stats['duplicate_reports']}")
        logger.info(f"Unique reports saved: {stats['unique_reports']}")
        logger.info(f"Output directory: {output_dir}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        stats["error"] = str(e)
        stats["success"] = False

    return stats


def main():
    """Main entry point for the application."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Medical Report PDF Processor - Extract, analyze, and process scanned medical reports"
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to input PDF file containing medical reports",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="output",
        help="Path to output directory (default: output)",
    )
    parser.add_argument(
        "--config",
        "-c",
        help="Path to custom configuration file (JSON)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )

    args = parser.parse_args()

    # Load configuration
    config = get_config()

    # Override with custom config if provided
    if args.config:
        import json

        with open(args.config, "r") as f:
            custom_config = json.load(f)
            # Merge custom config (simple merge)
            for key in custom_config:
                if key in config:
                    config[key].update(custom_config[key])

    # Override log level if verbose
    if args.verbose:
        config["logging"]["level"] = "DEBUG"

    # Ensure directories exist
    ensure_directories()

    # Setup logging
    setup_logging(config)
    logger = logging.getLogger(__name__)

    # Verify input file exists
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    if not input_path.suffix.lower() == ".pdf":
        logger.error(f"Input file must be a PDF: {input_path}")
        sys.exit(1)

    # Process the PDF
    stats = process_pdf(str(input_path), args.output, config)

    # Exit with appropriate code
    if stats["success"]:
        logger.info("Processing completed successfully!")
        sys.exit(0)
    else:
        logger.error(f"Processing failed: {stats['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
