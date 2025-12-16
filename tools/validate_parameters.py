"""
Parameter Validation Script for Blank Page Detection.

This tool validates proposed parameters against labeled samples and compares
performance of different configurations.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import seaborn as sns

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.image_analyzer import ImageAnalyzer
from config.config import BLANK_DETECTION_CONFIG

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class ParameterValidator:
    """Validates blank detection parameters against labeled samples."""

    def __init__(self, samples_dir: str = "samples"):
        """
        Initialize the validator.

        Args:
            samples_dir: Directory containing samples and metrics.json
        """
        self.samples_dir = Path(samples_dir)
        self.metrics_file = self.samples_dir / "metrics.json"

        if not self.metrics_file.exists():
            raise FileNotFoundError(
                f"Metrics file not found: {self.metrics_file}\n"
                "Please run extract_samples.py first to create labeled samples."
            )

        # Load samples
        with open(self.metrics_file, "r") as f:
            metadata = json.load(f)

        self.samples = []
        blank_dir = self.samples_dir / "blank"
        non_blank_dir = self.samples_dir / "non_blank"

        for item in metadata:
            if item["category"] == "blank":
                img_path = blank_dir / item["filename"]
            else:
                img_path = non_blank_dir / item["filename"]

            if img_path.exists():
                self.samples.append(
                    {
                        "image": Image.open(img_path),
                        "true_label": item["category"],
                        "filename": item["filename"],
                    }
                )

        logger.info(f"Loaded {len(self.samples)} labeled samples for validation")

    def validate_config(self, config: Dict, config_name: str = "config") -> Dict:
        """
        Validate a configuration against the samples.

        Args:
            config: Configuration dictionary with blank_detection parameters
            config_name: Name for this configuration

        Returns:
            Dictionary containing validation metrics
        """
        logger.info(f"Validating {config_name}...")

        # Extract blank detection config
        if "blank_detection" in config:
            params = config["blank_detection"]
        else:
            params = config

        # Create analyzer
        analyzer = ImageAnalyzer(**params)

        # Validate against all samples
        results = {
            "tp": 0,  # True Positives
            "fp": 0,  # False Positives
            "tn": 0,  # True Negatives
            "fn": 0,  # False Negatives
            "misclassified": [],
        }

        for sample in self.samples:
            is_blank, metrics = analyzer.is_blank(sample["image"])
            predicted = "blank" if is_blank else "non_blank"
            true = sample["true_label"]

            if true == "blank" and predicted == "blank":
                results["tp"] += 1
            elif true == "non_blank" and predicted == "blank":
                results["fp"] += 1
                results["misclassified"].append(
                    {
                        "filename": sample["filename"],
                        "true": true,
                        "predicted": predicted,
                        "metrics": metrics,
                    }
                )
            elif true == "non_blank" and predicted == "non_blank":
                results["tn"] += 1
            elif true == "blank" and predicted == "non_blank":
                results["fn"] += 1
                results["misclassified"].append(
                    {
                        "filename": sample["filename"],
                        "true": true,
                        "predicted": predicted,
                        "metrics": metrics,
                    }
                )

        # Calculate metrics
        total = len(self.samples)
        tp, fp, tn, fn = results["tp"], results["fp"], results["tn"], results["fn"]

        results["accuracy"] = (tp + tn) / total if total > 0 else 0
        results["precision"] = tp / (tp + fp) if (tp + fp) > 0 else 0
        results["recall"] = tp / (tp + fn) if (tp + fn) > 0 else 0
        results["f1_score"] = (
            2 * results["precision"] * results["recall"] / (results["precision"] + results["recall"])
            if (results["precision"] + results["recall"]) > 0
            else 0
        )
        results["specificity"] = tn / (tn + fp) if (tn + fp) > 0 else 0

        # Add config info
        results["config_name"] = config_name
        results["parameters"] = params
        results["total_samples"] = total

        return results

    def compare_configs(
        self, configs: Dict[str, Dict], save_plot: str = None
    ) -> None:
        """
        Compare multiple configurations.

        Args:
            configs: Dictionary mapping config names to config dictionaries
            save_plot: Optional path to save comparison plot
        """
        logger.info(f"Comparing {len(configs)} configurations...")

        # Validate each config
        all_results = {}
        for name, config in configs.items():
            all_results[name] = self.validate_config(config, config_name=name)

        # Print comparison report
        self._print_comparison_report(all_results)

        # Plot comparison
        if save_plot or len(configs) > 1:
            self._plot_comparison(all_results, save_path=save_plot)

        return all_results

    def _print_comparison_report(self, results: Dict[str, Dict]) -> None:
        """Print a formatted comparison report."""
        print("\n" + "=" * 80)
        print("PARAMETER VALIDATION - COMPARISON REPORT")
        print("=" * 80)
        print()

        # Summary table
        print(f"{'Configuration':<20} {'Accuracy':<12} {'Precision':<12} {'Recall':<12} {'F1-Score':<12}")
        print("-" * 80)

        for name, result in results.items():
            print(
                f"{name:<20} {result['accuracy']:>10.1%}  {result['precision']:>10.1%}  "
                f"{result['recall']:>10.1%}  {result['f1_score']:>10.3f}"
            )

        print()

        # Detailed results for each config
        for name, result in results.items():
            print("=" * 80)
            print(f"CONFIGURATION: {name}")
            print("=" * 80)

            # Parameters
            print("\nParameters:")
            params = result["parameters"]
            print(f"  Variance Threshold:   {params.get('variance_threshold', 'N/A')}")
            print(f"  Edge Threshold:       {params.get('edge_threshold', 'N/A')}")
            print(
                f"  White Pixel Ratio:    {params.get('white_pixel_ratio', 'N/A'):.4f} ({params.get('white_pixel_ratio', 0):.1%})"
            )
            print(f"  Use Edge Detection:   {params.get('use_edge_detection', 'N/A')}")

            # Metrics
            print("\nPerformance Metrics:")
            print(f"  Accuracy:    {result['accuracy']:.1%}")
            print(f"  Precision:   {result['precision']:.1%}")
            print(f"  Recall:      {result['recall']:.1%}")
            print(f"  Specificity: {result['specificity']:.1%}")
            print(f"  F1-Score:    {result['f1_score']:.3f}")

            # Confusion matrix
            print("\nConfusion Matrix:")
            print(f"                 Predicted Blank    Predicted Non-Blank")
            print(f"  Actual Blank        {result['tp']:>6}             {result['fn']:>6}")
            print(f"  Actual Non-Blank    {result['fp']:>6}             {result['tn']:>6}")

            # Misclassified samples
            if result["misclassified"]:
                print(f"\nMisclassified Samples: {len(result['misclassified'])}")
                for i, sample in enumerate(result["misclassified"][:5], 1):
                    print(f"  {i}. {sample['filename']}")
                    print(f"     True: {sample['true']}, Predicted: {sample['predicted']}")
                    print(
                        f"     Variance: {sample['metrics']['variance']:.2f}, "
                        f"White Ratio: {sample['metrics']['white_ratio']:.2%}, "
                        f"Edges: {sample['metrics']['edge_count']}"
                    )

                if len(result["misclassified"]) > 5:
                    print(f"  ... and {len(result['misclassified']) - 5} more")

            print()

        print("=" * 80)

        # Recommendation
        best_config = max(results.items(), key=lambda x: x[1]["f1_score"])
        print(f"\nRECOMMENDATION: '{best_config[0]}' has the highest F1-score ({best_config[1]['f1_score']:.3f})")
        print("=" * 80)
        print()

    def _plot_comparison(self, results: Dict[str, Dict], save_path: str = None) -> None:
        """Create comparison visualization."""
        logger.info("Generating comparison plots...")

        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)

        # Metrics comparison
        ax1 = fig.add_subplot(gs[0, :2])
        config_names = list(results.keys())
        metrics = ["accuracy", "precision", "recall", "f1_score", "specificity"]
        metric_labels = ["Accuracy", "Precision", "Recall", "F1-Score", "Specificity"]

        x = np.arange(len(config_names))
        width = 0.15

        for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
            values = [results[name][metric] for name in config_names]
            ax1.bar(x + i * width, values, width, label=label)

        ax1.set_xlabel("Configuration")
        ax1.set_ylabel("Score")
        ax1.set_title("Performance Metrics Comparison", fontsize=14, weight="bold")
        ax1.set_xticks(x + width * 2)
        ax1.set_xticklabels(config_names, rotation=45, ha="right")
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis="y")
        ax1.set_ylim(0, 1.1)

        # F1-Score focus
        ax2 = fig.add_subplot(gs[0, 2])
        f1_scores = [results[name]["f1_score"] for name in config_names]
        colors = plt.cm.RdYlGn([score for score in f1_scores])
        ax2.barh(config_names, f1_scores, color=colors)
        ax2.set_xlabel("F1-Score")
        ax2.set_title("F1-Score Comparison", fontsize=12, weight="bold")
        ax2.grid(True, alpha=0.3, axis="x")
        ax2.set_xlim(0, 1.0)

        # Confusion matrices
        for idx, (name, result) in enumerate(results.items()):
            ax = fig.add_subplot(gs[1, idx % 3])

            confusion_matrix = np.array(
                [[result["tp"], result["fn"]], [result["fp"], result["tn"]]]
            )

            sns.heatmap(
                confusion_matrix,
                annot=True,
                fmt="d",
                cmap="Blues",
                xticklabels=["Pred Blank", "Pred Non-Blank"],
                yticklabels=["Actual Blank", "Actual Non-Blank"],
                ax=ax,
                cbar=True,
            )

            ax.set_title(f"{name}\nAccuracy: {result['accuracy']:.1%}", fontsize=10)

            if idx >= 2:  # Only show 3 confusion matrices
                break

        plt.suptitle("Blank Page Detection - Parameter Validation", fontsize=16, weight="bold")

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            logger.info(f"Comparison plot saved to: {save_path}")
        else:
            plt.show()


def load_config_file(config_path: str) -> Dict:
    """Load configuration from JSON file."""
    with open(config_path, "r") as f:
        return json.load(f)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate blank detection parameters against labeled samples"
    )
    parser.add_argument(
        "--samples-dir",
        type=str,
        default="samples",
        help="Directory containing samples and metrics.json",
    )
    parser.add_argument(
        "--config",
        type=str,
        action="append",
        help="Config file to validate (can be specified multiple times for comparison)",
    )
    parser.add_argument(
        "--compare-all",
        action="store_true",
        help="Compare current, optimized, and tuned configs",
    )
    parser.add_argument(
        "--plot-output",
        type=str,
        default="samples/validation_comparison.png",
        help="Path to save comparison plot",
    )

    args = parser.parse_args()

    try:
        validator = ParameterValidator(samples_dir=args.samples_dir)

        configs = {}

        if args.compare_all:
            # Load and compare all available configs
            configs["Current (Default)"] = {"blank_detection": BLANK_DETECTION_CONFIG}

            optimized_path = Path("config/optimized_config.json")
            if optimized_path.exists():
                configs["Optimized"] = load_config_file(str(optimized_path))

            tuned_path = Path("config/tuned_config.json")
            if tuned_path.exists():
                configs["Tuned"] = load_config_file(str(tuned_path))

            if len(configs) == 1:
                logger.warning(
                    "Only default config available. Run optimize_parameters.py first."
                )

        elif args.config:
            # Load specified configs
            for config_path in args.config:
                config_name = Path(config_path).stem
                configs[config_name] = load_config_file(config_path)

        else:
            # Just validate the optimized config
            optimized_path = Path("config/optimized_config.json")
            if optimized_path.exists():
                configs["Optimized"] = load_config_file(str(optimized_path))
            else:
                logger.error(
                    "No config specified and optimized_config.json not found. "
                    "Use --config or run optimize_parameters.py first."
                )
                sys.exit(1)

        # Validate and compare
        validator.compare_configs(configs, save_plot=args.plot_output)

    except Exception as e:
        logger.error(f"Error during validation: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
