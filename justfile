# Medical Report PDF Processor - Just Commands
# Usage: just <command>

# Default Python command
python := if os_family() == "windows" { "python" } else { "python3" }
venv_python := if os_family() == "windows" { "med_report/Scripts/python.exe" } else { "med_report/bin/python" }
venv_pip := if os_family() == "windows" { "med_report/Scripts/pip.exe" } else { "med_report/bin/pip" }

# Default recipe - show available commands
default:
    @just --list

# Install dependencies and set up virtual environment
install:
    @echo "Creating virtual environment..."
    {{python}} -m venv med_report
    @echo "Installing dependencies..."
    {{venv_pip}} install --upgrade pip
    {{venv_pip}} install -r requirements.txt
    @echo "Setup complete! Virtual environment created in med_report/"

# Install additional development dependencies
install-dev:
    {{venv_pip}} install -r requirements.txt
    {{venv_pip}} install black flake8 mypy
    @echo "Development dependencies installed!"

# Run the CLI processor
run INPUT OUTPUT="output":
    @echo "Processing PDF: {{INPUT}} -> {{OUTPUT}}"
    {{venv_python}} main.py --input "{{INPUT}}" --output "{{OUTPUT}}"

# Run with verbose logging
run-verbose INPUT OUTPUT="output":
    @echo "Processing PDF with verbose logging: {{INPUT}} -> {{OUTPUT}}"
    {{venv_python}} main.py --input "{{INPUT}}" --output "{{OUTPUT}}" --verbose

# Run with custom config
run-config INPUT OUTPUT="output" CONFIG="config/custom.json":
    @echo "Processing PDF with custom config: {{INPUT}}"
    {{venv_python}} main.py --input "{{INPUT}}" --output "{{OUTPUT}}" --config "{{CONFIG}}"

# Run all tests
test:
    @echo "Running tests with pytest..."
    {{venv_python}} -m pytest tests/ -v

# Run tests with coverage report
test-coverage:
    @echo "Running tests with coverage..."
    {{venv_python}} -m pytest tests/ --cov=src --cov=app --cov-report=html --cov-report=term
    @echo "Coverage report generated in htmlcov/"

# Run specific test file
test-file FILE:
    @echo "Running tests in {{FILE}}..."
    {{venv_python}} -m pytest {{FILE}} -v

# Start FastAPI development server
dev PORT="8000":
    @echo "Starting FastAPI development server on http://localhost:{{PORT}}"
    {{venv_python}} -m uvicorn app.main:app --reload --host 0.0.0.0 --port {{PORT}}

# Start FastAPI production server
serve PORT="8000":
    @echo "Starting FastAPI production server on http://localhost:{{PORT}}"
    {{venv_python}} -m uvicorn app.main:app --host 0.0.0.0 --port {{PORT}} --workers 4

# Format code with black
format:
    @echo "Formatting code with black..."
    {{venv_python}} -m black src/ app/ tests/ main.py

# Lint code with flake8
lint:
    @echo "Linting code with flake8..."
    {{venv_python}} -m flake8 src/ app/ tests/ main.py --max-line-length=100

# Type check with mypy
typecheck:
    @echo "Type checking with mypy..."
    {{venv_python}} -m mypy src/ app/ --ignore-missing-imports

# Run all quality checks (format, lint, typecheck, test)
check: format lint typecheck test
    @echo "All quality checks passed!"

# Build Docker image for production
docker-build TAG="latest":
    @echo "Building Docker image: med-report-processor:{{TAG}}"
    docker build -t med-report-processor:{{TAG}} .

# Build Docker image for development
docker-build-dev TAG="dev":
    @echo "Building Docker development image: med-report-processor:{{TAG}}"
    docker build -f Dockerfile.dev -t med-report-processor:{{TAG}} .

# Run Docker container
docker-run PORT="8000" INPUT_DIR="./input" OUTPUT_DIR="./output":
    @echo "Running Docker container on port {{PORT}}"
    docker run -d \
        --name med-report-processor \
        -p {{PORT}}:8000 \
        -v "{{INPUT_DIR}}:/app/input" \
        -v "{{OUTPUT_DIR}}:/app/output" \
        med-report-processor:latest

# Run Docker container in interactive mode
docker-run-interactive PORT="8000" INPUT_DIR="./input" OUTPUT_DIR="./output":
    @echo "Running Docker container interactively on port {{PORT}}"
    docker run -it --rm \
        -p {{PORT}}:8000 \
        -v "{{INPUT_DIR}}:/app/input" \
        -v "{{OUTPUT_DIR}}:/app/output" \
        med-report-processor:latest

# Stop and remove Docker container
docker-stop:
    @echo "Stopping Docker container..."
    docker stop med-report-processor || true
    docker rm med-report-processor || true

# Start services with docker-compose
docker-up:
    @echo "Starting services with docker-compose..."
    docker-compose up -d

# Stop services with docker-compose
docker-down:
    @echo "Stopping services with docker-compose..."
    docker-compose down

# View docker-compose logs
docker-logs:
    docker-compose logs -f

# Start production services with docker-compose
docker-up-prod:
    @echo "Starting production services..."
    docker-compose -f docker-compose.prod.yml up -d

# Stop production services
docker-down-prod:
    @echo "Stopping production services..."
    docker-compose -f docker-compose.prod.yml down

# Clean temporary files and output
clean:
    @echo "Cleaning temporary files..."
    rm -rf temp/*
    rm -rf output/*.pdf
    rm -rf output/*.json
    @echo "Cleaned temp/ and output/ directories"

# Clean Python cache files
clean-cache:
    @echo "Cleaning Python cache files..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
    @echo "Python cache cleaned!"

# Full clean (temp, output, cache, Docker)
clean-all: clean clean-cache docker-stop
    @echo "Full cleanup complete!"

# Verify installation and dependencies
verify:
    @echo "Verifying installation..."
    {{venv_python}} verify_setup.py

# Show project status
status:
    @echo "=== Project Status ==="
    @echo "Python: {{venv_python}}"
    @{{venv_python}} --version
    @echo ""
    @echo "Virtual environment: med_report/"
    @echo "Input directory: input/"
    @ls -lh input/ 2>/dev/null || echo "No files in input/"
    @echo ""
    @echo "Output directory: output/"
    @ls -lh output/*.pdf 2>/dev/null || echo "No PDFs in output/"
    @echo ""
    @echo "Docker images:"
    @docker images med-report-processor 2>/dev/null || echo "No Docker images found"

# Open API documentation in browser
docs:
    @echo "Starting server and opening API docs..."
    @echo "Visit http://localhost:8000/docs for API documentation"
    @{{venv_python}} -m uvicorn app.main:app --reload &
    sleep 2
    @if command -v xdg-open > /dev/null; then xdg-open http://localhost:8000/docs; \
     elif command -v open > /dev/null; then open http://localhost:8000/docs; \
     elif command -v start > /dev/null; then start http://localhost:8000/docs; \
     else echo "Please open http://localhost:8000/docs in your browser"; fi

# Create a sample input PDF for testing
sample:
    @echo "To test the processor, place a medical report PDF in the input/ directory"
    @echo "Then run: just run input/your-file.pdf"

# Show environment information
env:
    @echo "=== Environment Information ==="
    @echo "OS: {{os()}}"
    @echo "OS Family: {{os_family()}}"
    @echo "Python: {{venv_python}}"
    @{{venv_python}} --version
    @echo "Pip: {{venv_pip}}"
    @{{venv_pip}} --version
    @echo "Current directory: {{invocation_directory()}}"
    @echo "Justfile directory: {{justfile_directory()}}"
