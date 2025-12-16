"""
Verification script to test that all dependencies are installed correctly.
"""

import sys

def verify_imports():
    """Verify that all required packages can be imported."""
    print("Verifying package installations...\n")

    packages = {
        "NumPy": "numpy",
        "Pillow (PIL)": "PIL",
        "OpenCV": "cv2",
        "PyMuPDF (fitz)": "fitz",
        "ImageHash": "imagehash",
        "Pytesseract": "pytesseract",
        "img2pdf": "img2pdf",
        "tqdm": "tqdm",
    }

    all_ok = True

    for name, module in packages.items():
        try:
            imported = __import__(module)
            version = getattr(imported, "__version__", "unknown")
            print(f"[OK] {name:20} - Version: {version}")
        except ImportError as e:
            print(f"[FAIL] {name:20} - FAILED: {e}")
            all_ok = False

    print("\nVerifying project modules...\n")

    try:
        from src import PDFProcessor, ImageAnalyzer, ReportSplitter, DuplicateDetector, FileManager
        print("[OK] All project modules imported successfully")
    except ImportError as e:
        print(f"[FAIL] Project modules - FAILED: {e}")
        all_ok = False

    print("\n" + "="*60)

    if all_ok:
        print("SUCCESS: All dependencies are installed correctly!")
        print("\nYou can now run the application:")
        print("  python main.py --input input/yourfile.pdf --output output/")
    else:
        print("ERROR: Some dependencies are missing or failed to import.")
        print("Please install missing packages using:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    print("="*60)

if __name__ == "__main__":
    verify_imports()
