"""
Medical Report PDF Processor - Source Package

This package contains modules for processing scanned medical report PDFs.
"""

__version__ = "1.0.0"
__author__ = "Medical Report Processor Team"

from .pdf_processor import PDFProcessor
from .image_analyzer import ImageAnalyzer
from .report_splitter import ReportSplitter, Report
from .duplicate_detector import DuplicateDetector
from .file_manager import FileManager

__all__ = [
    "PDFProcessor",
    "ImageAnalyzer",
    "ReportSplitter",
    "Report",
    "DuplicateDetector",
    "FileManager",
]
