# Medical Report PDF Processor

A Python application that processes scanned medical report PDFs by extracting individual reports, removing blank pages, detecting duplicates, and saving processed reports separately.

## Features

- **PDF to Image Conversion**: Extracts pages from PDF files as high-quality images using PyMuPDF
- **Blank Page Detection**: Automatically identifies and removes blank or nearly-blank pages using multiple detection methods
- **Optional Report Splitting**: Intelligently splits multi-report PDFs into individual reports using pattern detection (can be disabled to treat entire PDF as one report)
- **Optional Duplicate Detection**: Uses perceptual hashing to identify and filter duplicate reports (can be disabled to keep all reports)
- **Flexible Processing Modes**: Choose which processing steps to run based on your needs
- **Flexible Output**: Save reports as PDF files, images, or both formats
- **Web UI & CLI**: Process PDFs via web interface or command line
- **Parameter Optimization Tools**: Data-driven tools to find optimal blank detection parameters
- **Configuration Presets**: Save and load different configuration sets (current, optimized, tuned)
- **Comprehensive Logging**: Detailed logs and metadata for audit trails

## Project Structure

```
med-report-processor/
├── src/                      # Source code modules
│   ├── pdf_processor.py      # PDF extraction and conversion
│   ├── image_analyzer.py     # Blank page detection
│   ├── report_splitter.py    # Report boundary detection
│   ├── duplicate_detector.py # Duplicate detection
│   └── file_manager.py       # File operations
├── app/                      # Web application
│   ├── api/                  # FastAPI routes and models
│   ├── core/                 # Business logic
│   ├── static/               # Web UI files (HTML, CSS, JS)
│   └── main.py               # Web server entry point
├── tools/                    # Parameter optimization tools
│   ├── extract_samples.py    # Sample extraction for optimization
│   ├── optimize_parameters.py # Automated parameter finder
│   ├── interactive_tuner.py  # Visual parameter tuning
│   ├── validate_parameters.py # Config validation
│   ├── run_with_config.py    # Run with different configs
│   ├── manage_config.py      # Config deployment manager
│   └── README.md             # Tools documentation
├── config/                   # Configuration
│   ├── config.py             # Settings and parameters
│   ├── optimized_config.json # Auto-optimized parameters (generated)
│   └── tuned_config.json     # Manually tuned parameters (generated)
├── tests/                    # Test files
├── input/                    # Input PDF files
├── output/                   # Processed reports
├── samples/                  # Sample pages for optimization
│   ├── blank/                # Labeled blank pages
│   └── non_blank/            # Labeled non-blank pages
├── main.py                   # CLI entry point
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── CLAUDE.md                 # Project instructions
```

## Installation

### Prerequisites

- Python 3.8 or higher
- Tesseract OCR (optional, for pattern detection)

**Installing Tesseract OCR:**

- **Windows**: Download from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- **Mac**: `brew install tesseract`
- **Linux**: `sudo apt-get install tesseract-ocr`

### Setup

1. Clone or download this repository

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
```bash
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Web Interface (Recommended)

The easiest way to use the processor is through the web UI:

1. **Start the web server:**
```bash
python app/main.py
```

2. **Open your browser:**
```
http://localhost:8000
```

3. **Upload and process:**
   - Drag and drop or click to upload a PDF
   - (Optional) Select configuration preset (Current, Optimized, or Tuned)
   - (Optional) Customize settings:
     - Enable/disable report splitting
     - Enable/disable duplicate detection
     - Adjust blank detection parameters
   - Click "Process PDF"
   - Monitor real-time progress
   - Download individual reports when complete

**Web UI Features:**
- Real-time progress tracking with WebSocket updates
- Configuration preset selector (current/optimized/tuned)
- Interactive parameter adjustment
- Job history tracking
- One-click report downloads

---

### Command-Line Interface

Process a PDF file with default settings:

```bash
python main.py --input input/medical_reports.pdf --output output/
```

### CLI Options

```bash
python main.py --help
```

**Available options:**

- `--input, -i`: Path to input PDF file (required)
- `--output, -o`: Path to output directory (default: output)
- `--config, -c`: Path to custom configuration file (JSON)
- `--verbose, -v`: Enable verbose logging (DEBUG level)

### Examples

**Process with custom output directory:**
```bash
python main.py -i input/reports.pdf -o processed_reports/
```

**Enable verbose logging:**
```bash
python main.py -i input/reports.pdf -o output/ --verbose
```

**Use custom configuration:**
```bash
python main.py -i input/reports.pdf -o output/ --config custom_config.json
```

## Configuration

The system can be configured by editing `config/config.py` or providing a custom JSON config file.

### Key Configuration Options

#### PDF Processing Settings

**`dpi` (Default: 200)**
- **What it does**: Controls the resolution when converting PDF pages to images
- **Values**: 72-600 (recommended: 150-300)
- **Impact**:
  - Higher DPI = Better quality but larger files and slower processing
  - Lower DPI = Faster processing but may affect OCR accuracy
- **When to adjust**:
  - Use 150 for faster processing on low-quality scans
  - Use 300 for high-quality output or better OCR results
  - Use 200 for balanced performance and quality

**`image_format` (Default: "PNG")**
- **What it does**: Image format for internal processing
- **Values**: "PNG" or "JPEG"
- **Impact**:
  - PNG: Lossless quality, larger files
  - JPEG: Compressed, smaller files but slight quality loss
- **When to adjust**: Use JPEG for faster processing with large PDFs

**`color_space` (Default: "RGB")**
- **What it does**: Color mode for image conversion
- **Values**: "RGB" or "GRAY"
- **Impact**:
  - RGB: Full color, larger memory usage
  - GRAY: Grayscale, 3x smaller memory footprint
- **When to adjust**: Use GRAY for black/white medical reports to save memory

---

#### Blank Page Detection Settings

**`variance_threshold` (Default: 100)**
- **What it does**: Measures pixel intensity variation to detect content
- **Values**: 0-500 (recommended: 50-200)
- **Impact**:
  - Lower values (50-80) = More aggressive, may remove pages with faint content
  - Higher values (150-200) = Less aggressive, may keep some blank pages
- **When to adjust**:
  - Increase if legitimate pages are being removed (faint scans)
  - Decrease if blank pages are not being detected
- **Example**: If a page with light watermarks is considered blank, increase to 150

**`edge_threshold` (Default: 50)**
- **What it does**: Counts edges detected in the image (content indicator)
- **Values**: 0-200 (recommended: 30-100)
- **Impact**:
  - Lower = Detects even small amounts of content
  - Higher = Requires more visible content to count as non-blank
- **When to adjust**: Increase if pages with only page numbers are kept as non-blank

**`white_pixel_ratio` (Default: 0.95)**
- **What it does**: Percentage of white/light pixels required to classify as blank
- **Values**: 0.80-0.99 (recommended: 0.90-0.97)
- **Impact**:
  - 0.95 = Page must be 95% white to be considered blank
  - Lower values = More aggressive blank detection
- **When to adjust**:
  - Decrease to 0.90 for pages with small headers/footers only
  - Increase to 0.97 for very conservative blank detection

**`use_edge_detection` (Default: True)**
- **What it does**: Enables Canny edge detection algorithm
- **Values**: True or False
- **Impact**: More accurate blank detection but slightly slower
- **When to adjust**: Disable for faster processing if accuracy is not critical

---

#### Report Splitting Settings

**`enabled` (Default: True)** ⭐ NEW
- **What it does**: Enable or disable report splitting entirely
- **Values**: True or False
- **Impact**:
  - True = Split PDF into individual reports based on headers
  - False = Treat entire PDF as a single report
- **When to adjust**:
  - Disable when you know the PDF contains only one report
  - Disable for fast processing when splitting is not needed
  - Disable to skip Step 3 of the pipeline
- **Example**: Set to False to just remove blank pages without analyzing report boundaries

**`use_ocr` (Default: True)**
- **What it does**: Uses Tesseract OCR to detect report headers
- **Values**: True or False
- **Impact**:
  - True = Accurate header detection, slower processing
  - False = Uses heuristic visual comparison, faster but less accurate
- **When to adjust**:
  - Disable if reports don't have text headers
  - Disable for faster processing if reports follow consistent visual patterns

**`ocr_language` (Default: "eng")**
- **What it does**: Language for OCR text recognition
- **Values**: "eng", "spa", "fra", "deu", etc. (Tesseract language codes)
- **Impact**: Affects OCR accuracy for header detection
- **When to adjust**: Set to match your report language
- **Multi-language**: Use "eng+spa" for multiple languages

**`header_detection_region` (Default: (0, 0, 1.0, 0.2))**
- **What it does**: Defines where to look for report headers (x1, y1, x2, y2 as ratios)
- **Values**: (0, 0, 1.0, 0.2) means top 20% of page
- **Impact**: Determines scanning area for new report detection
- **When to adjust**:
  - (0, 0, 1.0, 0.15) for headers in top 15%
  - (0, 0, 1.0, 0.3) if headers are lower on the page

**`header_keywords` (Default: ["patient name", "patient id", ...])**
- **What it does**: Keywords that indicate a new report is starting
- **Values**: List of strings
- **Impact**: Determines which pages are identified as report starts
- **When to adjust**: Customize for your specific report types
- **Example**: Add "lab results", "radiology report", "doctor: "

**`min_confidence` (Default: 60)**
- **What it does**: Minimum OCR confidence score (0-100) to accept text
- **Values**: 0-100 (recommended: 50-80)
- **Impact**:
  - Lower = Accepts more uncertain OCR results (more false positives)
  - Higher = Only accepts clear text (may miss some headers)
- **When to adjust**:
  - Decrease to 50 for poor quality scans
  - Increase to 75 for high-quality scans to avoid false detections

---

#### Duplicate Detection Settings

**`enabled` (Default: True)** ⭐ NEW
- **What it does**: Enable or disable duplicate detection entirely
- **Values**: True or False
- **Impact**:
  - True = Detect and remove duplicate reports
  - False = Keep all reports, even if they are duplicates
- **When to adjust**:
  - Disable when you want to manually review potential duplicates
  - Disable when you need to preserve all copies (e.g., for audit purposes)
  - Disable to skip Step 4 of the pipeline
  - Disable for faster processing when duplicates are not a concern
- **Example**: Set to False when processing reports where duplicates are intentional

**`hash_algorithm` (Default: "phash")**
- **What it does**: Algorithm for generating perceptual hashes
- **Values**: "phash", "dhash", "whash", "average_hash"
- **Characteristics**:
  - **phash**: Most robust to transformations, best for similar images
  - **dhash**: Fast, good for detecting differences
  - **whash**: Wavelet-based, good for texture comparison
  - **average_hash**: Fastest but least accurate
- **When to adjust**: Use "dhash" for faster processing, "phash" for accuracy

**`hash_size` (Default: 8)**
- **What it does**: Size of the hash (8x8 = 64-bit hash)
- **Values**: 8, 16, 32
- **Impact**:
  - 8 = Fast, may miss subtle differences
  - 16 = More sensitive, slower
- **When to adjust**: Use 16 for stricter duplicate detection

**`similarity_threshold` (Default: 0.95)**
- **What it does**: How similar images must be to be considered duplicates
- **Values**: 0.0-1.0 (recommended: 0.90-0.98)
- **Impact**:
  - 0.95 = 95% similar to be considered duplicate
  - Lower = More duplicates detected (less strict)
  - Higher = Fewer duplicates detected (more strict)
- **When to adjust**:
  - Decrease to 0.90 if reports with minor differences should be duplicates
  - Increase to 0.97 if only exact copies should be duplicates
- **Example**: 0.95 will catch rescanned pages with slight variations

**`hamming_distance_threshold` (Default: 5)**
- **What it does**: Maximum allowed bit differences in hash comparison
- **Values**: 0-20 (recommended: 3-10)
- **Impact**:
  - Lower values = Stricter duplicate detection
  - Higher values = More lenient duplicate detection
- **Relationship**: Works with hash_algorithm to determine duplicates
- **When to adjust**:
  - Use 3 for only near-identical images
  - Use 10 for detecting similar reports with minor variations

**`compare_first_page_only` (Default: False)**
- **What it does**: Only compares first pages of multi-page reports
- **Values**: True or False
- **Impact**:
  - True = Much faster for multi-page reports
  - False = More accurate, compares all pages
- **When to adjust**: Enable for speed if first pages are unique identifiers

---

#### File Management Settings

**`output_format` (Default: "pdf")**
- **What it does**: Format for saving processed reports
- **Values**: "pdf", "images", or "both"
- **Impact**:
  - "pdf" = Standard PDF files only
  - "images" = Individual page images (PNG/JPEG)
  - "both" = PDF + individual images (2x storage)
- **When to adjust**: Use "images" for downstream image processing

**`naming_pattern` (Default: "report_{index:04d}")**
- **What it does**: Template for output filenames
- **Values**: String with placeholders
- **Placeholders**: {index}, {date}, {time}
- **Examples**:
  - "report_{index:04d}" → report_0001.pdf
  - "medical_report_{index:03d}" → medical_report_001.pdf
  - "report_{date}_{index}" → report_2025-01-21_1.pdf

**`include_metadata` (Default: True)**
- **What it does**: Saves JSON metadata files alongside reports
- **Values**: True or False
- **Impact**: Creates {filename}_metadata.json with processing info
- **When to adjust**: Disable to reduce file clutter

**`compress_output` (Default: False)**
- **What it does**: Apply compression to output PDFs
- **Values**: True or False
- **Impact**:
  - True = Smaller files, slightly slower
  - False = Larger files, faster
- **When to adjust**: Enable for storage optimization

**`keep_temp_files` (Default: False)**
- **What it does**: Retain temporary processing files
- **Values**: True or False
- **Impact**: Useful for debugging but uses disk space
- **When to adjust**: Enable for troubleshooting or inspection

---

### Configuration Tuning Guide

**For High Quality Scans:**
```json
{
  "pdf": {"dpi": 300},
  "blank_detection": {"variance_threshold": 150},
  "duplicate_detection": {"similarity_threshold": 0.97}
}
```

**For Blank Page Removal Only (Fastest):** ⭐ NEW
```json
{
  "report_splitting": {"enabled": false},
  "duplicate_detection": {"enabled": false}
}
```
This skips Steps 3 & 4, only removing blank pages. Useful when you just need a cleaned-up PDF.

**For Splitting Without Deduplication:** ⭐ NEW
```json
{
  "report_splitting": {"enabled": true, "use_ocr": true},
  "duplicate_detection": {"enabled": false}
}
```
Splits PDF into individual reports but keeps all copies, even duplicates.

**For Fast Processing:**
```json
{
  "pdf": {"dpi": 150, "color_space": "GRAY"},
  "report_splitting": {"use_ocr": false},
  "duplicate_detection": {"compare_first_page_only": true}
}
```

**For Low Quality/Faded Scans:**
```json
{
  "pdf": {"dpi": 250},
  "blank_detection": {
    "variance_threshold": 50,
    "white_pixel_ratio": 0.90
  },
  "report_splitting": {"min_confidence": 50}
}
```

**For Strict Duplicate Detection:**
```json
{
  "duplicate_detection": {
    "hash_size": 16,
    "similarity_threshold": 0.98,
    "hamming_distance_threshold": 3
  }
}
```

### Custom Configuration File Example

Create a JSON file (e.g., `custom_config.json`):

```json
{
  "blank_detection": {
    "variance_threshold": 150,
    "white_pixel_ratio": 0.90
  },
  "duplicate_detection": {
    "similarity_threshold": 0.98,
    "hamming_distance_threshold": 3
  },
  "file_management": {
    "output_format": "both",
    "naming_pattern": "report_{date}_{index:03d}"
  }
}
```

Use it with:
```bash
python main.py -i input/reports.pdf -c custom_config.json
```

## Output

The processor generates:

1. **Individual Report PDFs**: Each unique report saved as a separate PDF
2. **Metadata Files**: JSON files containing processing metadata
3. **Processing Log**: `processing_log.json` with statistics and timestamps
4. **Application Log**: `processing.log` with detailed execution logs

### Output File Structure

```
output/
├── report_0001.pdf
├── report_0001_metadata.json
├── report_0002.pdf
├── report_0002_metadata.json
├── ...
├── processing_log.json
└── processing.log (in project root)
```

## Processing Pipeline

The application follows a flexible 5-step pipeline where Steps 3 and 4 can be optionally disabled:

1. **PDF Extraction**: Convert PDF pages to images *(Always runs)*
2. **Blank Detection**: Remove blank or nearly-blank pages *(Always runs)*
3. **Report Splitting**: Identify individual report boundaries *(Optional - can be disabled via `enabled: False`)*
4. **Duplicate Detection**: Find and remove duplicate reports *(Optional - can be disabled via `enabled: False`)*
5. **Save Output**: Generate output files with metadata *(Always runs)*

**Processing Modes:**
- **Full Pipeline**: All 5 steps run (default behavior)
- **Blank Removal Only**: Steps 1, 2, and 5 (Steps 3 & 4 disabled) - Fastest, just removes blank pages
- **Split Without Dedup**: Steps 1, 2, 3, and 5 (Step 4 disabled) - Splits reports but keeps all copies
- **Custom**: Any combination based on your needs

## Troubleshooting

### Common Issues

**ImportError: No module named 'pytesseract'**
- Install pytesseract: `pip install pytesseract`
- Or disable OCR in config: Set `use_ocr: False`

**TesseractNotFoundError**
- Install Tesseract OCR system-wide (see Prerequisites)
- Or disable OCR in config

**Low quality output**
- Increase DPI in config: `dpi: 300`
- Ensure input PDF has good scan quality

**Too many/few blanks detected**
- Adjust `variance_threshold` in blank detection config
- Lower value = more aggressive blank detection
- Higher value = less aggressive

**Reports not splitting correctly**
- Enable OCR: Set `use_ocr: True`
- Customize `header_keywords` for your report types
- Adjust `min_confidence` if OCR accuracy is low

**Too many duplicates detected**
- Increase `hamming_distance_threshold` (less strict)
- Decrease `similarity_threshold`

## Advanced Usage

### Using as a Python Module

```python
from src import PDFProcessor, ImageAnalyzer, ReportSplitter, DuplicateDetector, FileManager

# Initialize components
pdf_processor = PDFProcessor(dpi=200)
image_analyzer = ImageAnalyzer()
report_splitter = ReportSplitter(use_ocr=True)
duplicate_detector = DuplicateDetector()
file_manager = FileManager(output_dir="output")

# Process PDF
pages = pdf_processor.extract_pages("input.pdf")
non_blank_pages, _, _ = image_analyzer.filter_blank_pages(pages)
reports = report_splitter.split_reports(non_blank_pages)
report_pages = [r.pages for r in reports]
unique_reports = duplicate_detector.filter_duplicates(report_pages)

# Save results
file_manager.save_reports(unique_reports)
```

## Privacy and Security

This tool processes medical reports which contain sensitive patient information:

- All processing is done **locally** on your machine
- No data is sent to external servers
- Consider using encryption for stored PDFs
- Follow HIPAA or relevant data protection guidelines
- Use secure file deletion for temporary files

## Performance Optimization

For large PDFs:

- Process in batches if memory is limited
- Reduce DPI if file size is not critical (e.g., 150 instead of 200)
- Disable OCR if report splitting is not needed
- Use `compare_first_page_only: True` for faster duplicate detection

## Contributing

Contributions are welcome! Areas for improvement:

- Enhanced OCR accuracy
- Machine learning-based report splitting
- Additional output formats
- Performance optimizations
- Test coverage

## License

This project is provided as-is for educational and authorized use purposes.

## Support

For issues, questions, or feature requests, please create an issue in the project repository.

## Version

Current version: 1.1.0

## Changelog

### v1.1.0 (Latest)
- **NEW**: Optional report splitting - can be disabled via UI or config
- **NEW**: Optional duplicate detection - can be disabled via UI or config
- **NEW**: Web UI with real-time progress tracking and WebSocket updates
- **NEW**: Configuration preset system (current/optimized/tuned)
- **NEW**: Parameter optimization toolkit with 6 data-driven tools
- **NEW**: API endpoints for config management (`/api/configs/list`, `/api/configs/{name}`)
- **IMPROVED**: Flexible processing modes (full pipeline, blank removal only, split without dedup)
- **IMPROVED**: Enhanced UI with checkboxes for enabling/disabling processing steps

### v1.0.0 (Initial Release)
- PDF to image extraction
- Blank page detection
- Report splitting with OCR
- Perceptual hash-based duplicate detection
- Flexible output formats
- Comprehensive logging and metadata
