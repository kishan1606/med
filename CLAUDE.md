# Project Overview

Medical Report PDF Processor - A Python application with both web UI and CLI that processes scanned medical report PDFs by extracting individual reports, removing blank pages, detecting duplicates, and saving processed reports separately. Features optional report splitting and duplicate detection that can be enabled/disabled via UI or configuration.

## Tech Stack

- **Language**: Python 3.8+
- **Web Framework**: FastAPI (async web server with REST API)
- **Database**: None (file-based processing)
- **Key Libraries**:
  - **Core Processing**:
    - PyMuPDF (fitz) - PDF to image conversion
    - Pillow (PIL) - Image manipulation
    - OpenCV - Image analysis and blank page detection
    - imagehash - Perceptual hashing for duplicate detection
    - pytesseract - OCR for pattern detection (optional)
    - img2pdf - PDF generation
  - **Web & API**:
    - FastAPI - Web framework and REST API
    - uvicorn - ASGI server
    - websockets - Real-time progress updates
    - pydantic - Request/response validation
  - **Optimization Tools**:
    - matplotlib - Interactive parameter tuning UI
    - numpy - Statistical analysis
    - scipy - Advanced optimization (if needed)
- **Build Tools**: pip, virtualenv/venv

## Project Structure

```
/src                    - Core processing modules
  - pdf_processor.py      # PDF extraction and page-to-image conversion
  - image_analyzer.py     # Blank page detection using image analysis
  - report_splitter.py    # Pattern detection and report boundary identification
  - duplicate_detector.py # Hash-based duplicate report detection
  - file_manager.py       # Output file management and saving
/app                    - Web application (FastAPI)
  /api                    # API routes and models
    - routes.py             # REST API endpoints
    - models.py             # Pydantic request/response models
  /core                   # Business logic
    - tasks.py              # Background task management
    - processor.py          # Async processing wrapper
  /static                 # Web UI assets
    - index.html            # Main UI
    - app.js                # Frontend JavaScript
    - style.css             # Styling
  - main.py               # Web server entry point
/tools                  - Parameter optimization toolkit
  - extract_samples.py    # Extract and label sample pages
  - optimize_parameters.py # Statistical parameter optimization
  - interactive_tuner.py  # Visual parameter tuning GUI
  - validate_parameters.py # Config validation
  - run_with_config.py    # Run with different configs
  - manage_config.py      # Config deployment manager
/tests                  - Test files
/config                 - Configuration files
  - config.py             # Default configuration
  - optimized_config.json # Auto-generated optimal params (created by tools)
  - tuned_config.json     # Manually tuned params (created by tools)
/input                  - Input PDF files (scanned medical reports)
/output                 - Processed individual reports
/samples                - Sample pages for optimization
  /blank                  # Labeled blank pages
  /non_blank              # Labeled non-blank pages
main.py                 - CLI entry point
requirements.txt        - Python dependencies
README.md               - User documentation
CLAUDE.md               - Project instructions (this file)
```

## Development Setup

### Prerequisites
- Python 3.8 or higher
- Tesseract OCR (optional, for pattern detection)
  - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
  - Mac: `brew install tesseract`
  - Linux: `sudo apt-get install tesseract-ocr`

### Installation
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Project

**Web UI (Recommended):**
```bash
# Start the web server
python app/main.py

# Then open browser to http://localhost:8000
```

**Command Line:**
```bash
# Process a single PDF file
python main.py --input input/medical_reports.pdf --output output/

# With custom configuration
python main.py --input input/reports.pdf --output output/ --config config/settings.json

# Using a configuration preset
python tools/run_with_config.py --config optimized --input input/reports.pdf
```

## Coding Conventions

- **Style Guide**: PEP 8 (Python Enhancement Proposal)
- **Naming Conventions**:
  - Files: snake_case (e.g., pdf_processor.py)
  - Functions/Variables: snake_case (e.g., extract_pages, page_count)
  - Classes: PascalCase (e.g., PDFProcessor, ImageAnalyzer)
  - Constants: UPPER_SNAKE_CASE (e.g., MIN_BLANK_THRESHOLD, DEFAULT_DPI)
- **Code Formatting**: Use Black formatter, type hints where applicable
- **Documentation**: Docstrings for all functions and classes (Google style)

## Important Patterns

### Architecture
- Modular design with single-responsibility principle
- Each module handles one specific aspect of processing
- Flexible pipeline architecture: PDF → Extract → Analyze → [Optional: Split] → [Optional: Detect Duplicates] → Save
- Web UI and CLI both use the same core processing modules
- Async processing with background tasks for web API
- Real-time progress updates via WebSockets

### Common Patterns
- **Error Handling**: Use try-except blocks with specific exceptions, log errors with context
- **Logging**: Use Python's logging module (INFO for progress, WARNING for issues, ERROR for failures)
- **Resource Management**: Use context managers (with statements) for file operations
- **Progress Tracking**: Use tqdm for long-running operations
- **Configuration**: Centralized config in config.py with defaults and overrides

## Key Files and Directories

**Core Processing:**
- `main.py` - CLI entry point, orchestrates the entire processing pipeline
- `src/pdf_processor.py` - PDF extraction using PyMuPDF, converts pages to images
- `src/image_analyzer.py` - Analyzes images for blank detection using OpenCV
- `src/report_splitter.py` - Detects report boundaries using pattern matching/OCR
- `src/duplicate_detector.py` - Uses perceptual hashing to find duplicate reports
- `src/file_manager.py` - Handles file I/O and saving processed reports

**Web Application:**
- `app/main.py` - FastAPI web server entry point
- `app/api/routes.py` - REST API endpoints (upload, process, download, config management)
- `app/api/models.py` - Pydantic models for request/response validation
- `app/core/processor.py` - Async wrapper for processing pipeline
- `app/core/tasks.py` - Background job manager with WebSocket support
- `app/static/` - Web UI files (HTML, CSS, JavaScript)

**Configuration:**
- `config/config.py` - Default configuration with environment variable support
- `config/optimized_config.json` - Auto-generated optimal parameters (from tools)
- `config/tuned_config.json` - Manually tuned parameters (from tools)

**Optimization Tools:**
- `tools/extract_samples.py` - Extract and label sample pages for optimization
- `tools/optimize_parameters.py` - Statistical analysis to find optimal thresholds
- `tools/interactive_tuner.py` - Visual GUI for real-time parameter tuning
- `tools/validate_parameters.py` - Validate and compare configurations
- `tools/run_with_config.py` - Run processing with different config presets
- `tools/manage_config.py` - Deploy and manage configurations with backups

## Testing

- **Testing Framework**: pytest
- **Running Tests**: `pytest tests/`
- **Test Coverage**: `pytest --cov=src tests/`
- **Test Data**: Place sample PDFs in `tests/fixtures/` for testing

## Processing Pipeline

The pipeline consists of 5 steps, where Steps 3 and 4 can be optionally disabled:

1. **PDF Extraction** - Convert PDF pages to images (PyMuPDF) - *Always runs*
2. **Blank Detection** - Identify and filter out blank pages (OpenCV) - *Always runs*
3. **Report Splitting** - Detect report boundaries using headers/footers (OCR/pattern matching) - *Optional (enabled by default)*
   - Can be disabled via `report_splitting.enabled = False` in config or via UI checkbox
   - When disabled, treats entire PDF as a single report
4. **Duplicate Detection** - Compare reports using perceptual hashing (imagehash) - *Optional (enabled by default)*
   - Can be disabled via `duplicate_detection.enabled = False` in config or via UI checkbox
   - When disabled, keeps all reports even if they are duplicates
5. **Save Output** - Generate individual PDFs for each unique report - *Always runs*

**Processing Modes:**
- Full pipeline: All 5 steps (default)
- Blank removal only: Steps 1, 2, 5 (fastest, just cleans up PDF)
- Split without dedup: Steps 1, 2, 3, 5 (keeps all report copies)
- Custom: Any combination based on needs

## Additional Context

Important considerations:
- **Privacy**: Medical reports contain sensitive patient data - ensure secure handling
  - All processing is done locally, no data sent to external servers
  - Web UI runs on localhost only by default
- **Performance**: Large PDFs may require batch processing to manage memory
  - Use lower DPI (150) for faster processing
  - Consider disabling report splitting/dedup if not needed
- **Accuracy**: Blank page detection threshold may need tuning based on scan quality
  - Use `tools/optimize_parameters.py` to find optimal parameters for your PDFs
  - Use `tools/interactive_tuner.py` for visual fine-tuning
- **Configuration Presets**: Three configuration modes available
  - **current**: Default config from config.py
  - **optimized**: Auto-generated optimal parameters (run `tools/optimize_parameters.py`)
  - **tuned**: Manually tuned parameters (run `tools/interactive_tuner.py`)
- **Optional Processing**: Steps 3 and 4 can be disabled
  - Disable report splitting for single-report PDFs (faster processing)
  - Disable duplicate detection when you want to manually review all reports
  - Both can be toggled via web UI or configuration files
- **OCR Dependency**: Tesseract OCR needed for pattern detection; architecture supports non-OCR fallback
- **Duplicate Threshold**: Similarity threshold (default 95%) may need adjustment
- **Image Quality**: Processing assumes reasonable scan quality (150+ DPI recommended)
- **API Endpoints**: Web UI provides REST API for integration
  - `/api/upload` - Upload PDF files
  - `/api/process` - Start processing job
  - `/api/jobs/{job_id}` - Get job status
  - `/api/configs/list` - List available config presets
  - `/api/configs/{name}` - Get specific config preset
  - `/api/download/{filename}` - Download processed reports
