"""
Sample Extraction Tool for Blank Page Detection Parameter Optimization.

This tool helps you build a labeled dataset of blank and non-blank pages from your PDFs
to enable data-driven parameter optimization.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf_processor import PDFProcessor
from src.image_analyzer import ImageAnalyzer
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class SampleExtractor:
    """Extracts and labels sample pages for parameter optimization."""

    def __init__(self, samples_dir: str = "samples"):
        """
        Initialize the sample extractor.

        Args:
            samples_dir: Directory to save samples
        """
        self.samples_dir = Path(samples_dir)
        self.blank_dir = self.samples_dir / "blank"
        self.non_blank_dir = self.samples_dir / "non_blank"
        self.metrics_file = self.samples_dir / "metrics.json"

        # Create directories
        self.blank_dir.mkdir(parents=True, exist_ok=True)
        self.non_blank_dir.mkdir(parents=True, exist_ok=True)

        self.pdf_processor = PDFProcessor(dpi=200)
        # Use very lenient thresholds to catch all potential blank pages
        self.analyzer = ImageAnalyzer(
            variance_threshold=1000.0,  # Very high to not miss anything
            edge_threshold=500,
            white_pixel_ratio=0.85,  # Lower threshold
        )

        self.samples_metadata = []

    def extract_from_pdf(
        self, pdf_path: str, mode: str = "interactive", auto_threshold: float = 0.7
    ) -> None:
        """
        Extract sample pages from a PDF.

        Args:
            pdf_path: Path to the PDF file
            mode: 'interactive' for manual labeling, 'auto' for automatic extraction
            auto_threshold: For auto mode, confidence threshold for classification
        """
        logger.info(f"Extracting samples from {pdf_path}")
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Extract all pages
        logger.info("Converting PDF pages to images...")
        pages = self.pdf_processor.extract_pages(str(pdf_path))
        logger.info(f"Extracted {len(pages)} pages")

        # Analyze all pages
        logger.info("Analyzing pages...")
        results = []
        for idx, page in enumerate(pages):
            is_blank, metrics = self.analyzer.is_blank(page)
            results.append({"page_num": idx + 1, "image": page, "metrics": metrics})

        if mode == "interactive":
            self._interactive_labeling(results, pdf_path.stem)
        elif mode == "auto":
            self._auto_extraction(results, pdf_path.stem, auto_threshold)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        # Save metadata
        self._save_metadata()
        logger.info(f"Sample extraction complete. Metadata saved to {self.metrics_file}")

    def _interactive_labeling(self, results: List[Dict], pdf_name: str) -> None:
        """
        Interactively label pages as blank or non-blank.

        Args:
            results: List of page analysis results
            pdf_name: Name of the source PDF
        """
        logger.info("Starting interactive labeling. Press:")
        logger.info("  'b' = blank page")
        logger.info("  'n' = non-blank page")
        logger.info("  's' = skip this page")
        logger.info("  'q' = quit labeling")
        print("\n" + "=" * 60)

        fig, ax = plt.subplots(figsize=(10, 12))
        plt.ion()  # Interactive mode

        blank_count = 0
        non_blank_count = 0
        skip_count = 0

        for result in results:
            page_num = result["page_num"]
            image = result["image"]
            metrics = result["metrics"]

            # Display the page
            ax.clear()
            ax.imshow(image)
            ax.axis("off")

            # Show metrics
            info_text = (
                f"Page {page_num}/{len(results)}\n"
                f"Variance: {metrics['variance']:.2f}\n"
                f"Edge Count: {metrics['edge_count']}\n"
                f"White Ratio: {metrics['white_ratio']:.2%}\n"
                f"Current Prediction: {'BLANK' if metrics['is_blank'] else 'NON-BLANK'}"
            )
            ax.text(
                0.02,
                0.98,
                info_text,
                transform=ax.transAxes,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
                fontsize=10,
                family="monospace",
            )

            plt.title(
                f"Classify this page: [B]lank | [N]on-blank | [S]kip | [Q]uit",
                fontsize=12,
                weight="bold",
            )
            plt.draw()
            plt.pause(0.1)

            # Get user input
            while True:
                choice = input(
                    f"\nPage {page_num}: Is this blank? [b/n/s/q]: "
                ).lower()

                if choice == "q":
                    logger.info("Labeling stopped by user")
                    plt.close()
                    print(
                        f"\nSummary: {blank_count} blank, {non_blank_count} non-blank, {skip_count} skipped"
                    )
                    return

                elif choice == "s":
                    skip_count += 1
                    logger.info(f"Skipped page {page_num}")
                    break

                elif choice == "b":
                    self._save_sample(image, metrics, "blank", pdf_name, page_num)
                    blank_count += 1
                    logger.info(f"Saved page {page_num} as BLANK")
                    break

                elif choice == "n":
                    self._save_sample(image, metrics, "non_blank", pdf_name, page_num)
                    non_blank_count += 1
                    logger.info(f"Saved page {page_num} as NON-BLANK")
                    break

                else:
                    print("Invalid choice. Use b/n/s/q")

        plt.close()
        print("\n" + "=" * 60)
        print(
            f"Labeling complete! {blank_count} blank, {non_blank_count} non-blank, {skip_count} skipped"
        )

    def _auto_extraction(
        self, results: List[Dict], pdf_name: str, threshold: float
    ) -> None:
        """
        Automatically extract samples based on analysis confidence.

        Args:
            results: List of page analysis results
            pdf_name: Name of the source PDF
            threshold: Minimum confidence threshold
        """
        logger.info(f"Auto-extracting samples with confidence >= {threshold}")

        blank_count = 0
        non_blank_count = 0

        for result in results:
            page_num = result["page_num"]
            image = result["image"]
            metrics = result["metrics"]
            is_blank = metrics["is_blank"]

            # Calculate confidence based on how many criteria agreed
            blank_indicators = len(metrics.get("reasons", []))
            max_indicators = 3 if self.analyzer.use_edge_detection else 2
            confidence = blank_indicators / max_indicators

            # Save if confidence is high enough
            if confidence >= threshold:
                category = "blank" if is_blank else "non_blank"
                self._save_sample(image, metrics, category, pdf_name, page_num)

                if is_blank:
                    blank_count += 1
                else:
                    non_blank_count += 1

                logger.info(
                    f"Page {page_num}: {category.upper()} (confidence: {confidence:.1%})"
                )

        logger.info(
            f"Auto-extraction complete: {blank_count} blank, {non_blank_count} non-blank"
        )

    def _save_sample(
        self, image: Image.Image, metrics: dict, category: str, pdf_name: str, page_num: int
    ) -> None:
        """
        Save a sample image and its metadata.

        Args:
            image: PIL Image to save
            metrics: Analysis metrics
            category: 'blank' or 'non_blank'
            pdf_name: Source PDF name
            page_num: Page number
        """
        # Save image
        filename = f"{pdf_name}_page_{page_num:04d}.png"
        if category == "blank":
            filepath = self.blank_dir / filename
        else:
            filepath = self.non_blank_dir / filename

        image.save(filepath)

        # Store metadata
        metadata = {
            "filename": filename,
            "category": category,
            "source_pdf": pdf_name,
            "page_num": page_num,
            "metrics": {
                "variance": float(metrics["variance"]),
                "edge_count": int(metrics["edge_count"])
                if metrics["edge_count"] is not None
                else None,
                "white_ratio": float(metrics["white_ratio"]),
                "mean_pixel": float(metrics["mean_pixel"]),
                "std_dev": float(metrics["std_dev"]),
            },
        }
        self.samples_metadata.append(metadata)

    def _save_metadata(self) -> None:
        """Save all metadata to JSON file."""
        # Load existing metadata if any
        existing_metadata = []
        if self.metrics_file.exists():
            with open(self.metrics_file, "r") as f:
                existing_metadata = json.load(f)

        # Merge and save
        all_metadata = existing_metadata + self.samples_metadata
        with open(self.metrics_file, "w") as f:
            json.dump(all_metadata, f, indent=2)

    def show_summary(self) -> None:
        """Display summary statistics of collected samples."""
        if not self.metrics_file.exists():
            logger.warning("No samples found. Run extraction first.")
            return

        with open(self.metrics_file, "r") as f:
            metadata = json.load(f)

        blank_samples = [m for m in metadata if m["category"] == "blank"]
        non_blank_samples = [m for m in metadata if m["category"] == "non_blank"]

        print("\n" + "=" * 60)
        print("SAMPLE COLLECTION SUMMARY")
        print("=" * 60)
        print(f"Total samples: {len(metadata)}")
        print(f"  Blank pages: {len(blank_samples)}")
        print(f"  Non-blank pages: {len(non_blank_samples)}")
        print(f"\nSample directory: {self.samples_dir.absolute()}")
        print(f"Metadata file: {self.metrics_file.absolute()}")

        if blank_samples:
            print("\n--- Blank Page Statistics ---")
            variances = [m["metrics"]["variance"] for m in blank_samples]
            white_ratios = [m["metrics"]["white_ratio"] for m in blank_samples]
            edge_counts = [
                m["metrics"]["edge_count"]
                for m in blank_samples
                if m["metrics"]["edge_count"] is not None
            ]

            print(f"Variance: min={min(variances):.2f}, max={max(variances):.2f}")
            print(
                f"White Ratio: min={min(white_ratios):.2%}, max={max(white_ratios):.2%}"
            )
            if edge_counts:
                print(f"Edge Count: min={min(edge_counts)}, max={max(edge_counts)}")

        print("=" * 60 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract sample pages for blank detection parameter optimization"
    )
    parser.add_argument(
        "--pdf",
        type=str,
        required=True,
        help="Path to PDF file to extract samples from",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["interactive", "auto"],
        default="interactive",
        help="Extraction mode: interactive (manual labeling) or auto (automatic)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="For auto mode: minimum confidence threshold (0-1)",
    )
    parser.add_argument(
        "--samples-dir",
        type=str,
        default="samples",
        help="Directory to save samples",
    )
    parser.add_argument(
        "--summary", action="store_true", help="Show summary of collected samples"
    )

    args = parser.parse_args()

    extractor = SampleExtractor(samples_dir=args.samples_dir)

    if args.summary:
        extractor.show_summary()
    else:
        try:
            extractor.extract_from_pdf(args.pdf, mode=args.mode, auto_threshold=args.threshold)
            extractor.show_summary()
        except Exception as e:
            logger.error(f"Error extracting samples: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
