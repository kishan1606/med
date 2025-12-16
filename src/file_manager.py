"""
File Manager module for saving processed reports and managing output files.

This module handles saving individual reports as PDFs or image files,
along with metadata and processing logs.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import json
from PIL import Image
import img2pdf

logger = logging.getLogger(__name__)


class FileManager:
    """
    Manages file operations for saving processed reports.
    """

    def __init__(
        self,
        output_dir: str,
        output_format: str = "pdf",
        naming_pattern: str = "report_{index:04d}",
        include_metadata: bool = True,
        compress_output: bool = False,
        keep_temp_files: bool = False,
    ):
        """
        Initialize the File Manager.

        Args:
            output_dir: Directory to save output files
            output_format: Output format (pdf, images, both)
            naming_pattern: Naming pattern for output files (supports {index}, {date}, {time})
            include_metadata: Whether to save metadata JSON files
            compress_output: Whether to compress PDF outputs
            keep_temp_files: Whether to keep temporary files for debugging
        """
        self.output_dir = Path(output_dir)
        self.output_format = output_format.lower()
        self.naming_pattern = naming_pattern
        self.include_metadata = include_metadata
        self.compress_output = compress_output
        self.keep_temp_files = keep_temp_files

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"FileManager initialized: output_dir={output_dir}, "
            f"format={output_format}, pattern={naming_pattern}"
        )

    def save_report(
        self,
        pages: List[Image.Image],
        index: int,
        metadata: Optional[Dict] = None,
        original_filename: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Save a single report to disk.

        Args:
            pages: List of PIL Images comprising the report
            index: Report index/number
            metadata: Optional metadata dictionary
            original_filename: Original input PDF filename (without extension)

        Returns:
            Dictionary with paths to saved files
        """
        if not pages:
            logger.warning(f"Report {index} has no pages, skipping save")
            return {}

        # Generate filename
        filename = self._generate_filename(index, original_filename)

        saved_files = {}

        # Save based on output format
        if self.output_format in ["pdf", "both"]:
            pdf_path = self._save_as_pdf(pages, filename)
            saved_files["pdf"] = str(pdf_path)
            logger.info(f"Saved report {index} as PDF: {pdf_path}")

        if self.output_format in ["images", "both"]:
            image_dir = self._save_as_images(pages, filename)
            saved_files["images"] = str(image_dir)
            logger.info(f"Saved report {index} as images: {image_dir}")

        # Save metadata if requested
        if self.include_metadata:
            metadata_path = self._save_metadata(filename, pages, metadata)
            saved_files["metadata"] = str(metadata_path)

        return saved_files

    def save_reports(
        self,
        reports_pages: List[List[Image.Image]],
        reports_metadata: Optional[List[Dict]] = None,
    ) -> List[Dict[str, str]]:
        """
        Save multiple reports to disk.

        Args:
            reports_pages: List of reports, each containing a list of pages
            reports_metadata: Optional list of metadata dictionaries

        Returns:
            List of dictionaries with paths to saved files
        """
        logger.info(f"Saving {len(reports_pages)} reports to {self.output_dir}")

        if reports_metadata is None:
            reports_metadata = [None] * len(reports_pages)

        saved_files_list = []

        for idx, (pages, metadata) in enumerate(zip(reports_pages, reports_metadata)):
            try:
                saved_files = self.save_report(pages, idx + 1, metadata)
                saved_files_list.append(saved_files)
            except Exception as e:
                logger.error(f"Error saving report {idx + 1}: {e}")
                saved_files_list.append({})

        logger.info(f"Successfully saved {len(saved_files_list)} reports")
        return saved_files_list

    def _generate_filename(self, index: int, original_filename: Optional[str] = None) -> str:
        """
        Generate a filename based on the naming pattern.

        Args:
            index: Report index
            original_filename: Original input PDF filename (without extension)

        Returns:
            Filename (without extension)
        """
        now = datetime.now()

        # Clean original filename (remove extension and sanitize)
        if original_filename:
            # Remove .pdf extension if present
            clean_name = original_filename.replace('.pdf', '').replace('.PDF', '')
            # Remove any path separators
            clean_name = clean_name.replace('\\', '_').replace('/', '_')
            # Remove special characters
            clean_name = ''.join(c if c.isalnum() or c in '_-' else '_' for c in clean_name)
        else:
            clean_name = "report"

        # Build filename with original name prefix, report number, and timestamp suffix
        filename = f"{clean_name}_report_{index:04d}_{now.strftime('%Y%m%d_%H%M%S')}"

        return filename

    def _save_as_pdf(self, pages: List[Image.Image], filename: str) -> Path:
        """
        Save report pages as a PDF file.

        Args:
            pages: List of PIL Images
            filename: Base filename (without extension)

        Returns:
            Path to saved PDF file
        """
        pdf_path = self.output_dir / f"{filename}.pdf"

        # Convert PIL Images to bytes
        image_bytes = []
        for page in pages:
            # Convert to RGB if necessary (img2pdf requires RGB or L mode)
            if page.mode not in ["RGB", "L"]:
                page = page.convert("RGB")

            # Save to bytes
            from io import BytesIO

            img_byte_arr = BytesIO()
            page.save(img_byte_arr, format="PNG")
            image_bytes.append(img_byte_arr.getvalue())

        # Create PDF
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(image_bytes))

        return pdf_path

    def _save_as_images(self, pages: List[Image.Image], filename: str) -> Path:
        """
        Save report pages as individual image files.

        Args:
            pages: List of PIL Images
            filename: Base filename

        Returns:
            Path to directory containing images
        """
        # Create directory for this report's images
        image_dir = self.output_dir / filename
        image_dir.mkdir(exist_ok=True)

        # Save each page
        for idx, page in enumerate(pages):
            image_path = image_dir / f"page_{idx + 1:03d}.png"
            page.save(image_path, "PNG")

        return image_dir

    def _save_metadata(
        self, filename: str, pages: List[Image.Image], metadata: Optional[Dict]
    ) -> Path:
        """
        Save metadata as a JSON file.

        Args:
            filename: Base filename
            pages: List of pages (for extracting info)
            metadata: Metadata dictionary

        Returns:
            Path to metadata file
        """
        metadata_path = self.output_dir / f"{filename}_metadata.json"

        # Build metadata
        meta = {
            "filename": filename,
            "page_count": len(pages),
            "processed_at": datetime.now().isoformat(),
            "image_dimensions": [{"width": p.width, "height": p.height} for p in pages],
        }

        # Add user-provided metadata
        if metadata:
            meta.update(metadata)

        # Save to JSON
        with open(metadata_path, "w") as f:
            json.dump(meta, f, indent=2)

        return metadata_path

    def create_processing_log(self, log_data: Dict) -> Path:
        """
        Create a processing log file.

        Args:
            log_data: Dictionary containing processing statistics and info

        Returns:
            Path to log file
        """
        log_path = self.output_dir / "processing_log.json"

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            **log_data,
        }

        # Append to existing log or create new
        if log_path.exists():
            with open(log_path, "r") as f:
                try:
                    logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
        else:
            logs = []

        logs.append(log_entry)

        with open(log_path, "w") as f:
            json.dump(logs, f, indent=2)

        logger.info(f"Processing log saved: {log_path}")
        return log_path

    def cleanup_temp_files(self, temp_dir: str):
        """
        Clean up temporary files.

        Args:
            temp_dir: Path to temporary directory
        """
        temp_path = Path(temp_dir)

        if not temp_path.exists():
            return

        # Don't cleanup if keep_temp_files is True
        if self.keep_temp_files:
            logger.info(f"Keeping temporary files in {temp_dir} (keep_temp_files=True)")
            return

        logger.info(f"Cleaning up temporary files in {temp_dir}")

        # Remove all files in temp directory
        for item in temp_path.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    # Recursively remove directory
                    import shutil

                    shutil.rmtree(item)
            except Exception as e:
                logger.error(f"Error removing {item}: {e}")

    def get_output_summary(self) -> Dict:
        """
        Get a summary of output files.

        Returns:
            Dictionary with output statistics
        """
        pdf_files = list(self.output_dir.glob("*.pdf"))
        metadata_files = list(self.output_dir.glob("*_metadata.json"))
        image_dirs = [d for d in self.output_dir.iterdir() if d.is_dir()]

        summary = {
            "output_directory": str(self.output_dir),
            "pdf_count": len(pdf_files),
            "metadata_count": len(metadata_files),
            "image_directory_count": len(image_dirs),
            "total_size_mb": self._get_directory_size(self.output_dir) / (1024 * 1024),
        }

        return summary

    def _get_directory_size(self, directory: Path) -> int:
        """
        Calculate total size of a directory in bytes.

        Args:
            directory: Path to directory

        Returns:
            Total size in bytes
        """
        total = 0
        for item in directory.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
        return total


if __name__ == "__main__":
    # Setup basic logging for testing
    logging.basicConfig(level=logging.INFO)

    # Example usage
    file_manager = FileManager(output_dir="output", output_format="pdf")

    # Create test image
    test_image = Image.new("RGB", (800, 1000), color="white")
    test_pages = [test_image]

    # Save test report
    saved = file_manager.save_report(test_pages, index=1, metadata={"test": "data"})
    print(f"Saved files: {saved}")

    # Get summary
    summary = file_manager.get_output_summary()
    print(f"Output summary: {summary}")
