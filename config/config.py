"""
Configuration settings for the Medical Report PDF Processor.

This module contains all configurable parameters for PDF processing,
image analysis, duplicate detection, and output management.

Supports environment variable overrides for all settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Helper function to get environment variable with default
def get_env(key: str, default, type_cast=str):
    """Get environment variable with type casting and default value."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        if type_cast == bool:
            return value.lower() in ('true', '1', 'yes', 'on')
        return type_cast(value)
    except (ValueError, TypeError):
        return default

# Tesseract OCR Configuration
# Common Tesseract installation paths
COMMON_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",  # Standard Windows install
    r"D:\Program Files\Tesseract-OCR\tesseract.exe",  # Alternative drive
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",  # 32-bit
    "/usr/bin/tesseract",  # Linux
    "/usr/local/bin/tesseract",  # Mac/Linux alternative
    "/opt/homebrew/bin/tesseract",  # Mac M1/M2
]

# Try to find Tesseract automatically
TESSERACT_CMD = get_env('TESSERACT_CMD', None)

if TESSERACT_CMD is None:
    # Try to find Tesseract in common paths
    for path in COMMON_TESSERACT_PATHS:
        if os.path.exists(path):
            TESSERACT_CMD = path
            break

# Configure pytesseract if available
try:
    import pytesseract
    # Only set tesseract_cmd if we found a specific path
    # Otherwise, let pytesseract use the system PATH
    if TESSERACT_CMD and os.path.exists(TESSERACT_CMD):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    # If Tesseract is in PATH, pytesseract will find it automatically
except ImportError:
    pass

# Base directories
BASE_DIR = Path(__file__).parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"

# PDF Processing settings
PDF_CONFIG = {
    "dpi": get_env("PDF_DPI", 200, int),
    "image_format": get_env("PDF_IMAGE_FORMAT", "PNG"),
    "color_space": get_env("PDF_COLOR_SPACE", "RGB"),
}

# Blank Page Detection settings
BLANK_DETECTION_CONFIG = {
    "variance_threshold": get_env("VARIANCE_THRESHOLD", 100, float),
    "edge_threshold": get_env("EDGE_THRESHOLD", 50, int),
    "white_pixel_ratio": get_env("WHITE_PIXEL_RATIO", 0.95, float),
    "use_edge_detection": get_env("USE_EDGE_DETECTION", True, bool),
    "canny_low": 50,  # Canny edge detection low threshold
    "canny_high": 150,  # Canny edge detection high threshold
}

# Report Splitting settings - COMMENTED OUT: Report splitting disabled
# REPORT_SPLITTING_CONFIG = {
#     "enabled": get_env("ENABLE_REPORT_SPLITTING", False, bool),  # Disabled by default
#     "use_ocr": get_env("USE_OCR", True, bool),
#     "ocr_language": get_env("OCR_LANGUAGE", "eng"),
#     "header_detection_region": (0, 0, 1.0, 0.2),  # Top 20% of page (x1, y1, x2, y2 as ratios)
#     "footer_detection_region": (0, 0.8, 1.0, 1.0),  # Bottom 20% of page
#     "header_keywords": [
#         "patient name",
#         "patient id",
#         "medical record",
#         "report date",
#         "hospital",
#         "clinic",
#     ],
#     "min_confidence": get_env("MIN_CONFIDENCE", 60, int),
# }
REPORT_SPLITTING_CONFIG = {
    "enabled": False,  # Report splitting disabled
}

# Duplicate Detection settings
DUPLICATE_DETECTION_CONFIG = {
    "enabled": get_env("ENABLE_DUPLICATE_DETECTION", True, bool),
    "hash_algorithm": get_env("HASH_ALGORITHM", "phash"),
    "hash_size": get_env("HASH_SIZE", 8, int),
    "similarity_threshold": get_env("SIMILARITY_THRESHOLD", 0.95, float),
    "compare_first_page_only": False,  # Only compare first pages of reports
    "hamming_distance_threshold": get_env("HAMMING_DISTANCE_THRESHOLD", 5, int),
}

# File Management settings
FILE_MANAGEMENT_CONFIG = {
    "output_format": get_env("OUTPUT_FORMAT", "pdf"),
    "naming_pattern": "report_{index:04d}",  # Output file naming pattern
    "include_metadata": get_env("INCLUDE_METADATA", True, bool),
    "compress_output": get_env("COMPRESS_OUTPUT", False, bool),
    "keep_temp_files": get_env("KEEP_TEMP_FILES", False, bool),
}

# Logging settings
LOGGING_CONFIG = {
    "level": get_env("LOG_LEVEL", "INFO"),
    "format": get_env("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
    "file": BASE_DIR / get_env("LOG_FILE", "processing.log"),
    "console": get_env("LOG_CONSOLE", True, bool),
}

# Performance settings
PERFORMANCE_CONFIG = {
    "max_workers": 4,  # Number of parallel workers for processing
    "batch_size": 10,  # Number of pages to process in a batch
    "memory_limit_mb": 1024,  # Maximum memory usage in MB
}


def ensure_directories():
    """Create necessary directories if they don't exist."""
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)


def get_config():
    """
    Get the complete configuration dictionary.

    Returns:
        dict: Complete configuration settings
    """
    return {
        "pdf": PDF_CONFIG,
        "blank_detection": BLANK_DETECTION_CONFIG,
        "report_splitting": REPORT_SPLITTING_CONFIG,
        "duplicate_detection": DUPLICATE_DETECTION_CONFIG,
        "file_management": FILE_MANAGEMENT_CONFIG,
        "logging": LOGGING_CONFIG,
        "performance": PERFORMANCE_CONFIG,
        "directories": {
            "base": BASE_DIR,
            "input": INPUT_DIR,
            "output": OUTPUT_DIR,
            "temp": TEMP_DIR,
        },
    }


if __name__ == "__main__":
    # Print configuration for debugging
    import json

    config = get_config()
    print(json.dumps({k: str(v) if isinstance(v, Path) else v for k, v in config.items()}, indent=2))
