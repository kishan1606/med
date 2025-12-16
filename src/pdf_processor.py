"""
PDF Processor module for extracting pages from PDF files and converting them to images.

This module uses PyMuPDF (fitz) for efficient PDF processing and image extraction.
"""

import logging
from pathlib import Path
from typing import List, Tuple, Optional
import fitz  # PyMuPDF
from PIL import Image
import io

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    Handles PDF extraction and page-to-image conversion.
    """

    def __init__(self, dpi: int = 200, image_format: str = "PNG", color_space: str = "RGB"):
        """
        Initialize the PDF processor.

        Args:
            dpi: Resolution for image conversion (default: 200)
            image_format: Output image format (default: PNG)
            color_space: Color space for images (RGB or GRAY)
        """
        self.dpi = dpi
        self.image_format = image_format
        self.color_space = color_space
        self.zoom = dpi / 72  # PDF default is 72 DPI
        logger.info(f"PDFProcessor initialized with DPI={dpi}, format={image_format}")

    def extract_pages(self, pdf_path: str) -> List[Image.Image]:
        """
        Extract all pages from a PDF file as images.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of PIL Image objects, one per page

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If PDF processing fails
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Extracting pages from {pdf_path}")
        images = []

        try:
            # Open PDF document
            doc = fitz.open(pdf_path)
            logger.info(f"PDF contains {len(doc)} pages")

            # Process each page
            for page_num in range(len(doc)):
                logger.debug(f"Processing page {page_num + 1}/{len(doc)}")
                page = doc[page_num]

                # Create transformation matrix for desired DPI
                mat = fitz.Matrix(self.zoom, self.zoom)

                # Render page to pixmap
                pix = page.get_pixmap(matrix=mat, alpha=False)

                # Convert pixmap to PIL Image
                img_data = pix.tobytes(self.image_format.lower())
                img = Image.open(io.BytesIO(img_data))

                # Convert to desired color space
                if self.color_space == "GRAY" and img.mode != "L":
                    img = img.convert("L")
                elif self.color_space == "RGB" and img.mode != "RGB":
                    img = img.convert("RGB")

                images.append(img)

            doc.close()
            logger.info(f"Successfully extracted {len(images)} pages")
            return images

        except Exception as e:
            logger.error(f"Error extracting pages from PDF: {e}")
            raise

    def get_page_count(self, pdf_path: str) -> int:
        """
        Get the number of pages in a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Number of pages in the PDF

        Raises:
            FileNotFoundError: If PDF file doesn't exist
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            return page_count
        except Exception as e:
            logger.error(f"Error getting page count: {e}")
            raise

    def extract_page_range(
        self, pdf_path: str, start_page: int, end_page: int
    ) -> List[Image.Image]:
        """
        Extract a specific range of pages from a PDF.

        Args:
            pdf_path: Path to the PDF file
            start_page: Starting page number (0-indexed)
            end_page: Ending page number (exclusive, 0-indexed)

        Returns:
            List of PIL Image objects for the specified range

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If page range is invalid
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            if start_page < 0 or end_page > total_pages or start_page >= end_page:
                raise ValueError(
                    f"Invalid page range: {start_page}-{end_page} (total pages: {total_pages})"
                )

            logger.info(f"Extracting pages {start_page+1} to {end_page} from {pdf_path}")
            images = []

            for page_num in range(start_page, end_page):
                page = doc[page_num]
                mat = fitz.Matrix(self.zoom, self.zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_data = pix.tobytes(self.image_format.lower())
                img = Image.open(io.BytesIO(img_data))

                if self.color_space == "GRAY" and img.mode != "L":
                    img = img.convert("L")
                elif self.color_space == "RGB" and img.mode != "RGB":
                    img = img.convert("RGB")

                images.append(img)

            doc.close()
            logger.info(f"Successfully extracted {len(images)} pages")
            return images

        except Exception as e:
            logger.error(f"Error extracting page range: {e}")
            raise

    def get_metadata(self, pdf_path: str) -> dict:
        """
        Extract metadata from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary containing PDF metadata

        Raises:
            FileNotFoundError: If PDF file doesn't exist
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            metadata = {
                "page_count": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "modification_date": doc.metadata.get("modDate", ""),
            }
            doc.close()
            return metadata
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            raise


if __name__ == "__main__":
    # Setup basic logging for testing
    logging.basicConfig(level=logging.INFO)

    # Example usage
    processor = PDFProcessor(dpi=200)
    # Uncomment to test with an actual PDF file
    # images = processor.extract_pages("path/to/test.pdf")
    # print(f"Extracted {len(images)} pages")
