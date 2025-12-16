"""
Example Usage Script - Medical Report PDF Processor

This script demonstrates how to use the medical report processor
as a Python library rather than through the command-line interface.
"""

from pathlib import Path
from src import (
    PDFProcessor,
    ImageAnalyzer,
    ReportSplitter,
    DuplicateDetector,
    FileManager,
)
from config import get_config
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def process_pdf_example(input_pdf: str, output_dir: str):
    """
    Example: Process a PDF file step by step.

    Args:
        input_pdf: Path to input PDF file
        output_dir: Path to output directory
    """
    logger.info(f"Processing {input_pdf}")

    # Load configuration
    config = get_config()

    # Initialize components with configuration
    pdf_processor = PDFProcessor(**config["pdf"])
    image_analyzer = ImageAnalyzer(**config["blank_detection"])
    report_splitter = ReportSplitter(**config["report_splitting"])
    duplicate_detector = DuplicateDetector(**config["duplicate_detection"])
    file_manager = FileManager(output_dir, **config["file_management"])

    # Step 1: Extract pages from PDF
    logger.info("Step 1: Extracting pages...")
    pages = pdf_processor.extract_pages(input_pdf)
    logger.info(f"Extracted {len(pages)} pages")

    # Step 2: Remove blank pages
    logger.info("Step 2: Removing blank pages...")
    non_blank_pages, indices, metrics = image_analyzer.filter_blank_pages(pages)
    logger.info(f"Kept {len(non_blank_pages)} non-blank pages, removed {len(pages) - len(non_blank_pages)}")

    # Step 3: Split into reports
    logger.info("Step 3: Splitting into reports...")
    reports = report_splitter.split_reports(non_blank_pages)
    logger.info(f"Found {len(reports)} reports")

    # Step 4: Detect and remove duplicates
    logger.info("Step 4: Detecting duplicates...")
    report_pages = [report.pages for report in reports]
    unique_reports = duplicate_detector.filter_duplicates(report_pages)
    logger.info(f"{len(unique_reports)} unique reports (removed {len(reports) - len(unique_reports)} duplicates)")

    # Step 5: Save reports
    logger.info("Step 5: Saving reports...")
    saved_files = file_manager.save_reports(unique_reports)
    logger.info(f"Saved {len(saved_files)} reports to {output_dir}")

    return unique_reports, saved_files


def custom_configuration_example():
    """
    Example: Use custom configuration settings.
    """
    # Create custom PDF processor with high DPI
    pdf_processor = PDFProcessor(dpi=300, image_format="PNG", color_space="RGB")

    # Create custom blank detector with strict settings
    image_analyzer = ImageAnalyzer(
        variance_threshold=50,  # More strict
        white_pixel_ratio=0.98,
        use_edge_detection=True,
    )

    # Create duplicate detector with specific algorithm
    duplicate_detector = DuplicateDetector(
        hash_algorithm="dhash",  # Use difference hash
        hamming_distance_threshold=3,  # Very strict
    )

    logger.info("Custom components created successfully")
    return pdf_processor, image_analyzer, duplicate_detector


def analyze_single_image_example():
    """
    Example: Analyze a single image for blank detection.
    """
    from PIL import Image

    # Create analyzer
    analyzer = ImageAnalyzer()

    # Load or create an image
    # For demo, create a sample image
    sample_image = Image.new("RGB", (800, 1000), color="white")

    # Analyze the image
    is_blank, metrics = analyzer.is_blank(sample_image)

    logger.info(f"Image is blank: {is_blank}")
    logger.info(f"Metrics: {metrics}")

    # Get quality score
    quality = analyzer.get_image_quality_score(sample_image)
    logger.info(f"Quality score: {quality:.2f}/100")


def compare_reports_example():
    """
    Example: Compare two specific reports for similarity.
    """
    from PIL import Image

    # Create detector
    detector = DuplicateDetector(hash_algorithm="phash")

    # Create sample report pages
    report1_pages = [Image.new("RGB", (800, 1000), color="white")]
    report2_pages = [Image.new("RGB", (800, 1000), color="white")]

    # Compare the reports
    is_duplicate, similarity = detector.compare_two_reports(report1_pages, report2_pages)

    logger.info(f"Reports are duplicates: {is_duplicate}")
    logger.info(f"Similarity: {similarity:.2%}")


def batch_processing_example(pdf_files: list):
    """
    Example: Process multiple PDF files in batch.

    Args:
        pdf_files: List of paths to PDF files
    """
    config = get_config()
    pdf_processor = PDFProcessor(**config["pdf"])

    results = []

    for pdf_file in pdf_files:
        try:
            logger.info(f"Processing {pdf_file}")
            pages = pdf_processor.extract_pages(pdf_file)

            result = {
                "file": pdf_file,
                "page_count": len(pages),
                "status": "success",
            }
            results.append(result)

        except Exception as e:
            logger.error(f"Error processing {pdf_file}: {e}")
            results.append({"file": pdf_file, "status": "error", "error": str(e)})

    return results


def save_with_custom_naming():
    """
    Example: Save reports with custom naming patterns.
    """
    from PIL import Image

    # Create file manager with custom naming
    file_manager = FileManager(
        output_dir="custom_output",
        naming_pattern="medical_report_{date}_{index:03d}",
        output_format="both",  # Save as both PDF and images
        include_metadata=True,
    )

    # Create sample report
    sample_pages = [Image.new("RGB", (800, 1000), color="white")]

    # Save with custom metadata
    metadata = {
        "patient_id": "12345",
        "report_type": "Blood Test",
        "date": "2024-01-15",
    }

    saved = file_manager.save_report(sample_pages, index=1, metadata=metadata)
    logger.info(f"Saved files: {saved}")


if __name__ == "__main__":
    """
    Run examples (uncomment the one you want to test).
    """

    # Example 1: Full processing pipeline
    # Uncomment and provide an actual PDF file path to test
    # process_pdf_example("input/sample.pdf", "output")

    # Example 2: Custom configuration
    custom_configuration_example()

    # Example 3: Analyze single image
    analyze_single_image_example()

    # Example 4: Compare reports
    compare_reports_example()

    # Example 5: Batch processing
    # pdf_files = ["input/report1.pdf", "input/report2.pdf"]
    # batch_processing_example(pdf_files)

    # Example 6: Custom naming
    save_with_custom_naming()

    logger.info("Examples completed!")
