"""
Report Splitter module for identifying report boundaries in a sequence of pages.

This module uses OCR and pattern detection to identify where individual reports
begin and end in a multi-report PDF document.
"""

import logging
from typing import List, Tuple, Optional, Dict
import numpy as np
from PIL import Image
import re

# Optional OCR import
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("pytesseract not available. OCR-based splitting will be disabled.")

logger = logging.getLogger(__name__)


class Report:
    """Represents a single report with its pages and metadata."""

    def __init__(self, pages: List[Image.Image], page_indices: List[int], metadata: dict = None):
        """
        Initialize a Report.

        Args:
            pages: List of PIL Images comprising the report
            page_indices: List of original page indices in the source PDF
            metadata: Optional metadata dictionary
        """
        self.pages = pages
        self.page_indices = page_indices
        self.metadata = metadata or {}

    def __len__(self):
        return len(self.pages)

    def __repr__(self):
        return f"Report(pages={len(self.pages)}, indices={self.page_indices})"


class ReportSplitter:
    """
    Identifies report boundaries and splits a sequence of pages into individual reports.
    """

    def __init__(
        self,
        use_ocr: bool = True,
        ocr_language: str = "eng",
        header_detection_region: Tuple[float, float, float, float] = (0, 0, 1.0, 0.2),
        footer_detection_region: Tuple[float, float, float, float] = (0, 0.8, 1.0, 1.0),
        header_keywords: List[str] = None,
        min_confidence: int = 60,
    ):
        """
        Initialize the Report Splitter.

        Args:
            use_ocr: Whether to use OCR for pattern detection
            ocr_language: Tesseract language code
            header_detection_region: Region to search for headers (x1, y1, x2, y2 as ratios)
            footer_detection_region: Region to search for footers
            header_keywords: Keywords that indicate a report header
            min_confidence: Minimum OCR confidence score (0-100)
        """
        self.use_ocr = use_ocr and TESSERACT_AVAILABLE
        self.ocr_language = ocr_language
        self.header_detection_region = header_detection_region
        self.footer_detection_region = footer_detection_region
        self.header_keywords = header_keywords or [
            "patient name",
            "patient id",
            "medical record",
            "report date",
            "hospital",
            "clinic",
        ]
        self.min_confidence = min_confidence

        if self.use_ocr and not TESSERACT_AVAILABLE:
            logger.warning("OCR requested but pytesseract not available. Disabling OCR.")
            self.use_ocr = False

        logger.info(
            f"ReportSplitter initialized: use_ocr={self.use_ocr}, "
            f"language={ocr_language}, keywords={len(self.header_keywords)}"
        )

    def split_reports(self, images: List[Image.Image]) -> List[Report]:
        """
        Split a list of images into individual reports.

        Args:
            images: List of PIL Images to split

        Returns:
            List of Report objects
        """
        logger.info(f"Splitting {len(images)} pages into individual reports")

        if not images:
            return []

        # Detect report boundaries
        boundaries = self._detect_boundaries(images)

        # Create Report objects
        reports = []
        for start_idx, end_idx in boundaries:
            report_pages = images[start_idx:end_idx]
            page_indices = list(range(start_idx, end_idx))
            report = Report(
                pages=report_pages,
                page_indices=page_indices,
                metadata={"start_page": start_idx + 1, "end_page": end_idx},
            )
            reports.append(report)
            logger.info(f"Created report: pages {start_idx + 1} to {end_idx}")

        logger.info(f"Split into {len(reports)} reports")
        return reports

    def _detect_boundaries(self, images: List[Image.Image]) -> List[Tuple[int, int]]:
        """
        Detect report boundaries in the image sequence.

        Args:
            images: List of PIL Images

        Returns:
            List of (start_index, end_index) tuples for each report
        """
        if self.use_ocr:
            return self._detect_boundaries_ocr(images)
        else:
            return self._detect_boundaries_heuristic(images)

    def _detect_boundaries_ocr(self, images: List[Image.Image]) -> List[Tuple[int, int]]:
        """
        Detect report boundaries using OCR to find headers.

        Args:
            images: List of PIL Images

        Returns:
            List of (start_index, end_index) tuples
        """
        logger.info("Detecting boundaries using OCR")

        # Find pages with headers
        header_pages = []
        for idx, image in enumerate(images):
            if self._has_header(image):
                header_pages.append(idx)
                logger.debug(f"Header detected on page {idx + 1}")

        # If no headers found, treat entire sequence as one report
        if not header_pages:
            logger.warning("No headers detected. Treating all pages as single report.")
            return [(0, len(images))]

        # Create boundaries based on header positions
        boundaries = []
        for i, start_idx in enumerate(header_pages):
            if i < len(header_pages) - 1:
                end_idx = header_pages[i + 1]
            else:
                end_idx = len(images)
            boundaries.append((start_idx, end_idx))

        # If first header is not on first page, add initial report
        if header_pages[0] > 0:
            boundaries.insert(0, (0, header_pages[0]))

        return boundaries

    def _detect_boundaries_heuristic(self, images: List[Image.Image]) -> List[Tuple[int, int]]:
        """
        Detect report boundaries using heuristic methods (without OCR).

        This is a fallback method that looks for visual patterns like:
        - Significant changes in page layout
        - Presence of logos or headers (image-based detection)

        Args:
            images: List of PIL Images

        Returns:
            List of (start_index, end_index) tuples
        """
        logger.info("Detecting boundaries using heuristic methods (no OCR)")

        # Simple heuristic: look for pages with significantly different top regions
        # This can indicate a new report starting
        boundary_indices = [0]  # Always start at page 0

        for idx in range(1, len(images)):
            if self._is_likely_new_report(images[idx - 1], images[idx]):
                boundary_indices.append(idx)
                logger.debug(f"Potential boundary detected at page {idx + 1}")

        # Create boundaries
        boundaries = []
        for i in range(len(boundary_indices)):
            start_idx = boundary_indices[i]
            end_idx = boundary_indices[i + 1] if i + 1 < len(boundary_indices) else len(images)
            boundaries.append((start_idx, end_idx))

        # If no boundaries detected, treat as single report
        if len(boundaries) == 0:
            boundaries = [(0, len(images))]

        return boundaries

    def _has_header(self, image: Image.Image) -> bool:
        """
        Check if an image has a report header using OCR.

        Args:
            image: PIL Image to check

        Returns:
            True if header detected
        """
        # Extract header region
        width, height = image.size
        x1 = int(width * self.header_detection_region[0])
        y1 = int(height * self.header_detection_region[1])
        x2 = int(width * self.header_detection_region[2])
        y2 = int(height * self.header_detection_region[3])

        header_region = image.crop((x1, y1, x2, y2))

        # Perform OCR
        try:
            text = pytesseract.image_to_string(
                header_region, lang=self.ocr_language, config="--psm 6"
            ).lower()

            # Check for keywords
            for keyword in self.header_keywords:
                if keyword.lower() in text:
                    logger.debug(f"Header keyword found: {keyword}")
                    return True

        except Exception as e:
            logger.error(f"OCR error: {e}")

        return False

    def _is_likely_new_report(self, prev_image: Image.Image, current_image: Image.Image) -> bool:
        """
        Determine if current image likely starts a new report (heuristic method).

        Args:
            prev_image: Previous page image
            current_image: Current page image

        Returns:
            True if current page likely starts a new report
        """
        # Compare header regions of consecutive pages
        width, height = current_image.size
        x1 = int(width * self.header_detection_region[0])
        y1 = int(height * self.header_detection_region[1])
        x2 = int(width * self.header_detection_region[2])
        y2 = int(height * self.header_detection_region[3])

        prev_header = np.array(prev_image.crop((x1, y1, x2, y2)))
        curr_header = np.array(current_image.crop((x1, y1, x2, y2)))

        # Calculate difference
        diff = np.abs(prev_header.astype(float) - curr_header.astype(float))
        mean_diff = np.mean(diff)

        # If headers are significantly different, might be a new report
        threshold = 30  # Adjust based on testing
        return mean_diff > threshold


if __name__ == "__main__":
    # Setup basic logging for testing
    logging.basicConfig(level=logging.INFO)

    # Example usage
    splitter = ReportSplitter(use_ocr=False)  # Use heuristic method for testing

    # Create test images
    test_images = [Image.new("RGB", (800, 1000), color="white") for _ in range(5)]
    reports = splitter.split_reports(test_images)
    print(f"Split into {len(reports)} reports")
    for i, report in enumerate(reports):
        print(f"Report {i + 1}: {report}")
