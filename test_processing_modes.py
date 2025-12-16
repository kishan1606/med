"""Test script to verify all processing modes work correctly."""

import logging
from pathlib import Path
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from config.config import get_config
from main import process_pdf

def test_mode_b():
    """Test Mode B: Report Splitting ON, Duplicate Detection OFF"""
    print("\n" + "="*80)
    print("Testing Mode B: Report Splitting ON, Duplicate Detection OFF")
    print("="*80)

    config = get_config()
    config["report_splitting"]["enabled"] = True
    config["duplicate_detection"]["enabled"] = False

    input_file = "input/TEST_123_4.pdf"
    output_dir = "output_test_mode_b"

    if not Path(input_file).exists():
        print(f"ERROR: Input file not found: {input_file}")
        return False

    result = process_pdf(input_file, output_dir, config)

    print(f"\nResult:")
    print(f"  Success: {result['success']}")
    print(f"  Reports found: {result.get('reports_found', 0)}")
    print(f"  Unique reports: {result.get('unique_reports', 0)}")
    print(f"  Duplicate reports: {result.get('duplicate_reports', 0)}")

    # Check output files
    output_path = Path(output_dir)
    if output_path.exists():
        pdf_files = list(output_path.glob("*.pdf"))
        print(f"  PDF files created: {len(pdf_files)}")
        for pdf in pdf_files:
            print(f"    - {pdf.name} ({pdf.stat().st_size / 1024:.1f} KB)")
    else:
        print(f"  ERROR: Output directory not created!")

    return result['success']

def test_mode_c():
    """Test Mode C: Both Report Splitting and Duplicate Detection ON"""
    print("\n" + "="*80)
    print("Testing Mode C: Report Splitting ON, Duplicate Detection ON")
    print("="*80)

    config = get_config()
    config["report_splitting"]["enabled"] = True
    config["duplicate_detection"]["enabled"] = True

    input_file = "input/TEST_123_4.pdf"
    output_dir = "output_test_mode_c"

    if not Path(input_file).exists():
        print(f"ERROR: Input file not found: {input_file}")
        return False

    result = process_pdf(input_file, output_dir, config)

    print(f"\nResult:")
    print(f"  Success: {result['success']}")
    print(f"  Reports found: {result.get('reports_found', 0)}")
    print(f"  Unique reports: {result.get('unique_reports', 0)}")
    print(f"  Duplicate reports: {result.get('duplicate_reports', 0)}")

    # Check output files
    output_path = Path(output_dir)
    if output_path.exists():
        pdf_files = list(output_path.glob("*.pdf"))
        print(f"  PDF files created: {len(pdf_files)}")
        for pdf in pdf_files:
            print(f"    - {pdf.name} ({pdf.stat().st_size / 1024:.1f} KB)")
    else:
        print(f"  ERROR: Output directory not created!")

    return result['success']

if __name__ == "__main__":
    print("Medical Report PDF Processor - Processing Mode Tests")
    print("="*80)

    # Test Mode B
    mode_b_success = test_mode_b()

    # Test Mode C
    mode_c_success = test_mode_c()

    print("\n" + "="*80)
    print("Test Summary:")
    print("="*80)
    print(f"Mode B (Split without Dedup): {'PASS' if mode_b_success else 'FAIL'}")
    print(f"Mode C (Full Pipeline):        {'PASS' if mode_c_success else 'FAIL'}")
    print("="*80)

    sys.exit(0 if (mode_b_success and mode_c_success) else 1)
