"""
Interactive Parameter Tuning Tool for Blank Page Detection.

This tool provides a visual interface to adjust detection parameters in real-time
and see their impact on classification results.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, CheckButtons
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.image_analyzer import ImageAnalyzer

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class InteractiveTuner:
    """Interactive GUI for tuning blank detection parameters."""

    def __init__(self, samples_dir: str = "samples"):
        """
        Initialize the interactive tuner.

        Args:
            samples_dir: Directory containing sample images
        """
        self.samples_dir = Path(samples_dir)
        self.blank_dir = self.samples_dir / "blank"
        self.non_blank_dir = self.samples_dir / "non_blank"
        self.metrics_file = self.samples_dir / "metrics.json"

        # Load samples
        self.samples = self._load_samples()
        self.current_index = 0

        # Initialize parameters with default values
        self.params = {
            "variance_threshold": 100.0,
            "edge_threshold": 50,
            "white_pixel_ratio": 0.95,
            "use_edge_detection": True,
            "canny_low": 50,
            "canny_high": 150,
        }

        # Try to load optimized config if available
        self._load_optimized_config()

        # Create analyzer
        self.analyzer = ImageAnalyzer(**self.params)

        # GUI elements
        self.fig = None
        self.ax_image = None
        self.ax_metrics = None
        self.sliders = {}
        self.results_text = None

    def _load_samples(self) -> List[Dict]:
        """Load sample images and metadata."""
        if not self.metrics_file.exists():
            logger.warning(
                f"Metrics file not found: {self.metrics_file}. "
                "Loading images from directories only."
            )
            return self._load_from_directories()

        with open(self.metrics_file, "r") as f:
            metadata = json.load(f)

        samples = []
        for item in metadata:
            if item["category"] == "blank":
                img_path = self.blank_dir / item["filename"]
            else:
                img_path = self.non_blank_dir / item["filename"]

            if img_path.exists():
                samples.append(
                    {
                        "path": img_path,
                        "image": Image.open(img_path),
                        "true_label": item["category"],
                        "source_pdf": item.get("source_pdf", "unknown"),
                        "page_num": item.get("page_num", 0),
                    }
                )

        logger.info(f"Loaded {len(samples)} sample images")
        return samples

    def _load_from_directories(self) -> List[Dict]:
        """Load samples from directory structure when metadata is not available."""
        samples = []

        # Load blank pages
        if self.blank_dir.exists():
            for img_path in self.blank_dir.glob("*.png"):
                samples.append(
                    {
                        "path": img_path,
                        "image": Image.open(img_path),
                        "true_label": "blank",
                        "source_pdf": img_path.stem,
                        "page_num": 0,
                    }
                )

        # Load non-blank pages
        if self.non_blank_dir.exists():
            for img_path in self.non_blank_dir.glob("*.png"):
                samples.append(
                    {
                        "path": img_path,
                        "image": Image.open(img_path),
                        "true_label": "non_blank",
                        "source_pdf": img_path.stem,
                        "page_num": 0,
                    }
                )

        logger.info(f"Loaded {len(samples)} sample images from directories")
        return samples

    def _load_optimized_config(self) -> None:
        """Try to load optimized config as starting point."""
        config_path = Path("config") / "optimized_config.json"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    if "blank_detection" in config:
                        self.params.update(config["blank_detection"])
                        logger.info(f"Loaded optimized config from {config_path}")
            except Exception as e:
                logger.warning(f"Could not load optimized config: {e}")

    def _update_analyzer(self) -> None:
        """Update analyzer with current parameters."""
        self.analyzer = ImageAnalyzer(**self.params)

    def _analyze_current_sample(self) -> Dict:
        """Analyze current sample with current parameters."""
        sample = self.samples[self.current_index]
        is_blank, metrics = self.analyzer.is_blank(sample["image"])

        return {
            "predicted_label": "blank" if is_blank else "non_blank",
            "true_label": sample["true_label"],
            "is_correct": (is_blank and sample["true_label"] == "blank")
            or (not is_blank and sample["true_label"] == "non_blank"),
            "metrics": metrics,
        }

    def _analyze_all_samples(self) -> Dict:
        """Analyze all samples with current parameters."""
        results = {
            "correct": 0,
            "incorrect": 0,
            "true_positives": 0,
            "false_positives": 0,
            "true_negatives": 0,
            "false_negatives": 0,
        }

        for sample in self.samples:
            is_blank, _ = self.analyzer.is_blank(sample["image"])
            predicted = "blank" if is_blank else "non_blank"
            true = sample["true_label"]

            if predicted == true:
                results["correct"] += 1
            else:
                results["incorrect"] += 1

            # Confusion matrix
            if true == "blank" and predicted == "blank":
                results["true_positives"] += 1
            elif true == "non_blank" and predicted == "blank":
                results["false_positives"] += 1
            elif true == "non_blank" and predicted == "non_blank":
                results["true_negatives"] += 1
            elif true == "blank" and predicted == "non_blank":
                results["false_negatives"] += 1

        # Calculate metrics
        total = len(self.samples)
        results["accuracy"] = results["correct"] / total if total > 0 else 0

        tp = results["true_positives"]
        fp = results["false_positives"]
        fn = results["false_negatives"]

        results["precision"] = tp / (tp + fp) if (tp + fp) > 0 else 0
        results["recall"] = tp / (tp + fn) if (tp + fn) > 0 else 0
        results["f1_score"] = (
            2 * results["precision"] * results["recall"] / (results["precision"] + results["recall"])
            if (results["precision"] + results["recall"]) > 0
            else 0
        )

        return results

    def _update_display(self, val=None):
        """Update the display with current sample and parameters."""
        if not self.samples:
            return

        # Update parameters from sliders
        if val is not None:
            self.params["variance_threshold"] = self.sliders["variance"].val
            self.params["edge_threshold"] = int(self.sliders["edge"].val)
            self.params["white_pixel_ratio"] = self.sliders["white"].val
            self._update_analyzer()

        # Analyze current sample
        result = self._analyze_current_sample()
        sample = self.samples[self.current_index]

        # Display image
        self.ax_image.clear()
        self.ax_image.imshow(sample["image"])
        self.ax_image.axis("off")

        # Title with result
        correctness = "✓ CORRECT" if result["is_correct"] else "✗ INCORRECT"
        color = "green" if result["is_correct"] else "red"

        title = (
            f"Sample {self.current_index + 1}/{len(self.samples)} - {correctness}\n"
            f"True: {sample['true_label'].upper()} | "
            f"Predicted: {result['predicted_label'].upper()}"
        )
        self.ax_image.set_title(title, fontsize=12, weight="bold", color=color)

        # Display metrics
        self.ax_metrics.clear()
        self.ax_metrics.axis("off")

        metrics = result["metrics"]
        metrics_text = (
            f"CURRENT PAGE METRICS:\n\n"
            f"Variance: {metrics['variance']:.2f}\n"
            f"  (Threshold: {self.params['variance_threshold']:.2f})\n"
            f"  {'< BLANK' if metrics['variance'] < self.params['variance_threshold'] else '> NON-BLANK'}\n\n"
            f"White Ratio: {metrics['white_ratio']:.2%}\n"
            f"  (Threshold: {self.params['white_pixel_ratio']:.2%})\n"
            f"  {'> BLANK' if metrics['white_ratio'] > self.params['white_pixel_ratio'] else '< NON-BLANK'}\n\n"
            f"Edge Count: {metrics['edge_count']}\n"
            f"  (Threshold: {self.params['edge_threshold']})\n"
            f"  {'< BLANK' if metrics['edge_count'] < self.params['edge_threshold'] else '> NON-BLANK'}\n\n"
        )

        # Overall accuracy
        overall = self._analyze_all_samples()
        metrics_text += (
            f"─────────────────────────\n"
            f"OVERALL PERFORMANCE:\n\n"
            f"Accuracy: {overall['accuracy']:.1%}\n"
            f"Precision: {overall['precision']:.1%}\n"
            f"Recall: {overall['recall']:.1%}\n"
            f"F1-Score: {overall['f1_score']:.3f}\n\n"
            f"Correct: {overall['correct']}/{len(self.samples)}\n"
            f"TP: {overall['true_positives']}  FP: {overall['false_positives']}\n"
            f"TN: {overall['true_negatives']}  FN: {overall['false_negatives']}"
        )

        self.ax_metrics.text(
            0.05,
            0.95,
            metrics_text,
            transform=self.ax_metrics.transAxes,
            verticalalignment="top",
            fontsize=9,
            family="monospace",
            bbox=dict(boxstyle="round", facecolor="lightgray", alpha=0.8),
        )

        self.fig.canvas.draw_idle()

    def _next_sample(self, event):
        """Navigate to next sample."""
        self.current_index = (self.current_index + 1) % len(self.samples)
        self._update_display()

    def _prev_sample(self, event):
        """Navigate to previous sample."""
        self.current_index = (self.current_index - 1) % len(self.samples)
        self._update_display()

    def _save_config(self, event):
        """Save current parameters to config file."""
        config_path = Path("config") / "tuned_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "blank_detection": self.params.copy(),
            "tuning_metadata": {
                "samples_used": len(self.samples),
                "performance": self._analyze_all_samples(),
            },
        }

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        logger.info(f"Configuration saved to {config_path}")
        print(f"\n✓ Configuration saved to: {config_path.absolute()}")

    def run(self):
        """Run the interactive tuner GUI."""
        if not self.samples:
            logger.error("No samples found. Please run extract_samples.py first.")
            return

        # Create figure
        self.fig = plt.figure(figsize=(16, 10))
        self.fig.suptitle(
            "Interactive Blank Page Detection Parameter Tuner", fontsize=16, weight="bold"
        )

        # Layout
        gs = self.fig.add_gridspec(3, 2, height_ratios=[3, 1, 1], width_ratios=[2, 1])

        # Image display (left, top)
        self.ax_image = self.fig.add_subplot(gs[0, 0])

        # Metrics display (right, top)
        self.ax_metrics = self.fig.add_subplot(gs[0, 1])

        # Sliders (left, bottom)
        ax_slider_variance = self.fig.add_subplot(gs[1, 0])
        ax_slider_edge = self.fig.add_subplot(gs[2, 0])
        ax_slider_white = plt.axes([0.15, 0.15, 0.35, 0.03])

        # Create sliders
        self.sliders["variance"] = Slider(
            ax_slider_variance,
            "Variance Threshold",
            0.0,
            2000.0,
            valinit=self.params["variance_threshold"],
            valstep=10.0,
        )

        self.sliders["edge"] = Slider(
            ax_slider_edge,
            "Edge Threshold",
            0,
            1000,
            valinit=self.params["edge_threshold"],
            valstep=10,
        )

        self.sliders["white"] = Slider(
            ax_slider_white,
            "White Ratio",
            0.0,
            1.0,
            valinit=self.params["white_pixel_ratio"],
            valstep=0.01,
        )

        # Connect slider events
        self.sliders["variance"].on_changed(self._update_display)
        self.sliders["edge"].on_changed(self._update_display)
        self.sliders["white"].on_changed(self._update_display)

        # Navigation buttons
        ax_prev = plt.axes([0.55, 0.15, 0.08, 0.04])
        ax_next = plt.axes([0.64, 0.15, 0.08, 0.04])
        btn_prev = Button(ax_prev, "← Previous")
        btn_next = Button(ax_next, "Next →")
        btn_prev.on_clicked(self._prev_sample)
        btn_next.on_clicked(self._next_sample)

        # Save button
        ax_save = plt.axes([0.55, 0.08, 0.17, 0.04])
        btn_save = Button(ax_save, "Save Config", color="lightgreen")
        btn_save.on_clicked(self._save_config)

        # Initial display
        self._update_display()

        # Show GUI
        plt.tight_layout()
        plt.show()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive parameter tuner for blank page detection"
    )
    parser.add_argument(
        "--samples-dir",
        type=str,
        default="samples",
        help="Directory containing sample images",
    )

    args = parser.parse_args()

    try:
        tuner = InteractiveTuner(samples_dir=args.samples_dir)
        tuner.run()
    except Exception as e:
        logger.error(f"Error running interactive tuner: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
