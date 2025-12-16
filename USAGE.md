# Medical Report PDF Processor - Usage Guide

Complete guide for using the Medical Report PDF Processor with Just, Docker, and the Web UI.

## Table of Contents

- [Quick Start](#quick-start)
- [Using Just Commands](#using-just-commands)
- [Using Docker](#using-docker)
- [Using the Web UI](#using-the-web-ui)
- [Using the CLI](#using-the-cli)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Install Dependencies

**Option A: Local Installation**
```bash
# Install Just command runner (https://github.com/casey/just)
# Windows (via Scoop):
scoop install just

# Mac:
brew install just

# Install Python dependencies
just install
```

**Option B: Using Docker (No local Python needed)**
```bash
# Start with Docker Compose
docker-compose up -d

# Or build and run manually
just docker-build
just docker-run
```

### 2. Access the Application

**Web UI**: http://localhost:8000
**API Docs**: http://localhost:8000/docs
**Health Check**: http://localhost:8000/health

## Using Just Commands

`just` is a command runner that simplifies common tasks. Here are the available commands:

### Installation & Setup
```bash
# Install dependencies and create virtual environment
just install

# Install with development tools (black, flake8, mypy)
just install-dev

# Verify installation
just verify

# Check environment info
just env

# Show project status
just status
```

### Running the Application
```bash
# Run CLI processor
just run input/file.pdf output/

# Run with verbose logging
just run-verbose input/file.pdf output/

# Run with custom config
just run-config input/file.pdf output/ config/custom.json

# Start web development server (hot-reload)
just dev

# Start production web server
just serve

# Start on custom port
just dev 8080
```

### Development & Testing
```bash
# Run all tests
just test

# Run tests with coverage report
just test-coverage

# Run specific test file
just test-file tests/test_api.py

# Format code with black
just format

# Lint code with flake8
just lint

# Type check with mypy
just typecheck

# Run all quality checks
just check
```

### Docker Commands
```bash
# Build production Docker image
just docker-build

# Build development Docker image
just docker-build-dev

# Run Docker container
just docker-run

# Run interactively
just docker-run-interactive

# Stop and remove container
just docker-stop

# Start with docker-compose
just docker-up

# Stop docker-compose
just docker-down

# View logs
just docker-logs

# Production deployment
just docker-up-prod
just docker-down-prod
```

### Maintenance
```bash
# Clean temp files and output
just clean

# Clean Python cache files
just clean-cache

# Full cleanup (temp, cache, Docker)
just clean-all
```

## Using Docker

### Development with Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

The development setup includes:
- Hot-reload on code changes
- Volume mounts for source code
- Persistent input/output directories
- Debug logging enabled

### Production with Docker

```bash
# Build production image
docker build -t med-report-processor:latest .

# Run production container
docker run -d \
  --name med-report-processor \
  -p 8000:8000 \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  med-report-processor:latest

# Or use docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### Custom Configuration with Docker

```bash
# Create .env file (copy from .env.example)
cp .env.example .env

# Edit .env with your settings
# Then run with environment variables
docker-compose --env-file .env up -d
```

## Using the Web UI

### 1. Access the Web Interface

Open http://localhost:8000 in your browser.

### 2. Upload a PDF

- **Drag and drop** a PDF file onto the upload area, or
- **Click** the upload area to browse and select a file
- Maximum file size: 100 MB

### 3. Configure Settings (Optional)

Click "Show Options" to customize:

- **PDF Settings**: DPI, image format, color space
- **Blank Detection**: Thresholds for identifying blank pages
- **OCR Settings**: Enable/disable OCR, select language
- **Duplicate Detection**: Similarity thresholds

### 4. Process the PDF

Click "Process PDF" button to start processing.

### 5. Monitor Progress

Real-time progress updates via WebSocket:
- Current processing step
- Progress percentage
- Status messages

### 6. View and Download Results

When complete, you'll see:
- **Processing Statistics**: Total pages, blanks removed, reports found, duplicates
- **Individual Reports**: List of all processed reports
- **Download Buttons**: Download each report as PDF

### 7. View Processing History

The "Processing History" section shows all previous jobs with their status.

## Using the CLI

### Basic Usage

```bash
# Process a single PDF
python main.py --input input/medical_reports.pdf --output output/

# With verbose logging
python main.py --input input/file.pdf --output output/ --verbose

# With custom config
python main.py --input input/file.pdf --output output/ --config config/settings.json
```

### Custom Configuration File (JSON)

Create `config/custom.json`:
```json
{
  "pdf": {
    "dpi": 300
  },
  "blank_detection": {
    "variance_threshold": 150
  },
  "report_splitting": {
    "use_ocr": false
  }
}
```

Use it:
```bash
python main.py -i input/file.pdf -o output/ -c config/custom.json
```

## API Documentation

### Interactive API Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Main Endpoints

#### Upload File
```bash
POST /api/upload
Content-Type: multipart/form-data
Body: file (PDF)
```

#### Start Processing
```bash
POST /api/process?filename=yourfile.pdf
Content-Type: application/json
Body: { configuration options }
```

#### Check Job Status
```bash
GET /api/jobs/{job_id}
```

#### Download Report
```bash
GET /api/download/{filename}
```

#### WebSocket for Real-Time Progress
```
WS /api/ws/{job_id}
```

### Example API Usage (curl)

```bash
# Upload file
curl -X POST http://localhost:8000/api/upload \
  -F "file=@input/report.pdf"

# Start processing
curl -X POST "http://localhost:8000/api/process?filename=report.pdf" \
  -H "Content-Type: application/json" \
  -d '{}'

# Check status
curl http://localhost:8000/api/jobs/{job_id}

# Download result
curl -O http://localhost:8000/api/download/report_0001.pdf
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Key variables:
```env
# Tesseract path
TESSERACT_CMD=/usr/bin/tesseract

# Processing settings
PDF_DPI=200
USE_OCR=True
OCR_LANGUAGE=eng

# Performance
MAX_WORKERS=4
MEMORY_LIMIT_MB=2048

# Logging
LOG_LEVEL=INFO
```

### Python Configuration

Edit `config/config.py` for advanced customization:
- PDF processing parameters
- Blank detection thresholds
- Report splitting patterns
- Duplicate detection algorithms
- File management options

## Troubleshooting

### Tesseract Not Found

**Error**: "tesseract is not installed or it's not in your PATH"

**Solution**:
```bash
# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Install to: C:\Program Files\Tesseract-OCR

# Update config/config.py or set environment variable
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Linux/Mac
sudo apt-get install tesseract-ocr  # Ubuntu/Debian
brew install tesseract              # Mac
```

### Docker: Permission Denied

**Error**: Permission issues with mounted volumes

**Solution**:
```bash
# Ensure directories exist and have proper permissions
mkdir -p input output temp
chmod 777 input output temp  # Linux/Mac
```

### WebSocket Connection Failed

**Error**: WebSocket fails to connect

**Solution**:
- Ensure the server is running on the correct port
- Check firewall settings
- Try polling instead (automatic fallback)

### Out of Memory

**Error**: Processing fails with memory error

**Solution**:
```bash
# Reduce DPI in configuration
PDF_DPI=150

# Limit workers
MAX_WORKERS=2

# Or increase Docker memory limit in docker-compose.prod.yml
```

### Port Already in Use

**Error**: Port 8000 is already in use

**Solution**:
```bash
# Use different port
just dev 8080

# Or with Docker
docker run -p 9000:8000 ...
```

## Performance Tips

1. **For large PDFs**: Process in batches or reduce DPI
2. **For faster processing**: Disable OCR if not needed
3. **For better accuracy**: Increase DPI to 300
4. **For production**: Use docker-compose.prod.yml with resource limits

## Getting Help

- **Issues**: Report at GitHub Issues
- **API Docs**: http://localhost:8000/docs
- **Logs**: Check `processing.log`
- **Health**: http://localhost:8000/health

---

**Version**: 1.0.0
**Last Updated**: 2025-01-16
