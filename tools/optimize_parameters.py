"""
Automated Parameter Optimizer for Blank Page Detection.

This tool analyzes sample pages and automatically determines optimal threshold
parameters using statistical methods and ROC analysis.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class ParameterOptimizer:
    """Optimizes blank detection parameters based on labeled samples."""

    def __init__(self, samples_dir: str = "samples"):
        """
        Initialize the parameter optimizer.

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

        # Load sample data
        with open(self.metrics_file, "r") as f:
            self.samples = json.load(f)

        self.blank_samples = [s for s in self.samples if s["category"] == "blank"]
        self.non_blank_samples = [
            s for s in self.samples if s["category"] == "non_blank"
        ]

        logger.info(
            f"Loaded {len(self.blank_samples)} blank and {len(self.non_blank_samples)} non-blank samples"
        )

    def analyze_distributions(self) -> Dict:
        """
        Analyze the statistical distributions of metrics for blank and non-blank pages.

        Returns:
            Dictionary containing distribution statistics
        """
        logger.info("Analyzing metric distributions...")

        stats = {"blank": {}, "non_blank": {}}

        # Analyze blank pages
        if self.blank_samples:
            blank_variances = [s["metrics"]["variance"] for s in self.blank_samples]
            blank_white_ratios = [
                s["metrics"]["white_ratio"] for s in self.blank_samples
            ]
            blank_edge_counts = [
                s["metrics"]["edge_count"]
                for s in self.blank_samples
                if s["metrics"]["edge_count"] is not None
            ]

            stats["blank"] = {
                "variance": {
                    "min": np.min(blank_variances),
                    "max": np.max(blank_variances),
                    "mean": np.mean(blank_variances),
                    "median": np.median(blank_variances),
                    "p95": np.percentile(blank_variances, 95),
                    "p99": np.percentile(blank_variances, 99),
                },
                "white_ratio": {
                    "min": np.min(blank_white_ratios),
                    "max": np.max(blank_white_ratios),
                    "mean": np.mean(blank_white_ratios),
                    "median": np.median(blank_white_ratios),
                    "p5": np.percentile(blank_white_ratios, 5),
                    "p1": np.percentile(blank_white_ratios, 1),
                },
            }

            if blank_edge_counts:
                stats["blank"]["edge_count"] = {
                    "min": np.min(blank_edge_counts),
                    "max": np.max(blank_edge_counts),
                    "mean": np.mean(blank_edge_counts),
                    "median": np.median(blank_edge_counts),
                    "p95": np.percentile(blank_edge_counts, 95),
                    "p99": np.percentile(blank_edge_counts, 99),
                }

        # Analyze non-blank pages
        if self.non_blank_samples:
            non_blank_variances = [
                s["metrics"]["variance"] for s in self.non_blank_samples
            ]
            non_blank_white_ratios = [
                s["metrics"]["white_ratio"] for s in self.non_blank_samples
            ]
            non_blank_edge_counts = [
                s["metrics"]["edge_count"]
                for s in self.non_blank_samples
                if s["metrics"]["edge_count"] is not None
            ]

            stats["non_blank"] = {
                "variance": {
                    "min": np.min(non_blank_variances),
                    "max": np.max(non_blank_variances),
                    "mean": np.mean(non_blank_variances),
                    "median": np.median(non_blank_variances),
                    "p5": np.percentile(non_blank_variances, 5),
                    "p1": np.percentile(non_blank_variances, 1),
                },
                "white_ratio": {
                    "min": np.min(non_blank_white_ratios),
                    "max": np.max(non_blank_white_ratios),
                    "mean": np.mean(non_blank_white_ratios),
                    "median": np.median(non_blank_white_ratios),
                    "p95": np.percentile(non_blank_white_ratios, 95),
                    "p99": np.percentile(non_blank_white_ratios, 99),
                },
            }

            if non_blank_edge_counts:
                stats["non_blank"]["edge_count"] = {
                    "min": np.min(non_blank_edge_counts),
                    "max": np.max(non_blank_edge_counts),
                    "mean": np.mean(non_blank_edge_counts),
                    "median": np.median(non_blank_edge_counts),
                    "p5": np.percentile(non_blank_edge_counts, 5),
                    "p1": np.percentile(non_blank_edge_counts, 1),
                }

        return stats

    def find_optimal_threshold(
        self, blank_values: List[float], non_blank_values: List[float], higher_is_blank: bool
    ) -> Tuple[float, float, str]:
        """
        Find optimal threshold that best separates blank from non-blank pages.

        Args:
            blank_values: Metric values for blank pages
            non_blank_values: Metric values for non-blank pages
            higher_is_blank: True if higher values indicate blank (e.g., white_ratio),
                            False if lower values indicate blank (e.g., variance, edge_count)

        Returns:
            Tuple of (optimal_threshold, accuracy, justification)
        """
        if not blank_values or not non_blank_values:
            return None, 0.0, "Insufficient data"

        # Try different threshold candidates
        all_values = sorted(set(blank_values + non_blank_values))
        best_threshold = None
        best_accuracy = 0.0
        best_justification = ""

        for threshold in all_values:
            # Calculate true positives, false positives, etc.
            if higher_is_blank:
                # For white_ratio: blank pages should have HIGH values
                tp = sum(1 for v in blank_values if v >= threshold)
                fp = sum(1 for v in non_blank_values if v >= threshold)
                tn = sum(1 for v in non_blank_values if v < threshold)
                fn = sum(1 for v in blank_values if v < threshold)
            else:
                # For variance/edge_count: blank pages should have LOW values
                tp = sum(1 for v in blank_values if v <= threshold)
                fp = sum(1 for v in non_blank_values if v <= threshold)
                tn = sum(1 for v in non_blank_values if v > threshold)
                fn = sum(1 for v in blank_values if v > threshold)

            # Calculate accuracy
            total = len(blank_values) + len(non_blank_values)
            accuracy = (tp + tn) / total if total > 0 else 0

            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_threshold = threshold

                # Calculate precision and recall
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                f1 = (
                    2 * precision * recall / (precision + recall)
                    if (precision + recall) > 0
                    else 0
                )

                best_justification = (
                    f"Accuracy: {accuracy:.1%}, Precision: {precision:.1%}, "
                    f"Recall: {recall:.1%}, F1: {f1:.3f}"
                )

        return best_threshold, best_accuracy, best_justification

    def optimize_parameters(self) -> Dict:
        """
        Determine optimal parameters using statistical analysis.

        Returns:
            Dictionary containing optimized parameters and analysis
        """
        logger.info("Computing optimal parameters...")

        # Get metric arrays
        blank_variances = [s["metrics"]["variance"] for s in self.blank_samples]
        non_blank_variances = [s["metrics"]["variance"] for s in self.non_blank_samples]

        blank_white_ratios = [s["metrics"]["white_ratio"] for s in self.blank_samples]
        non_blank_white_ratios = [
            s["metrics"]["white_ratio"] for s in self.non_blank_samples
        ]

        blank_edge_counts = [
            s["metrics"]["edge_count"]
            for s in self.blank_samples
            if s["metrics"]["edge_count"] is not None
        ]
        non_blank_edge_counts = [
            s["metrics"]["edge_count"]
            for s in self.non_blank_samples
            if s["metrics"]["edge_count"] is not None
        ]

        # Find optimal thresholds
        optimal_variance, var_acc, var_just = self.find_optimal_threshold(
            blank_variances, non_blank_variances, higher_is_blank=False
        )

        optimal_white_ratio, white_acc, white_just = self.find_optimal_threshold(
            blank_white_ratios, non_blank_white_ratios, higher_is_blank=True
        )

        optimal_edge_count, edge_acc, edge_just = None, 0.0, ""
        if blank_edge_counts and non_blank_edge_counts:
            optimal_edge_count, edge_acc, edge_just = self.find_optimal_threshold(
                blank_edge_counts, non_blank_edge_counts, higher_is_blank=False
            )

        # Build recommendations
        recommendations = {
            "variance_threshold": {
                "value": round(optimal_variance, 2) if optimal_variance else 100.0,
                "accuracy": var_acc,
                "justification": var_just,
                "distribution": {
                    "blank_p95": round(np.percentile(blank_variances, 95), 2)
                    if blank_variances
                    else None,
                    "non_blank_p5": round(np.percentile(non_blank_variances, 5), 2)
                    if non_blank_variances
                    else None,
                },
            },
            "white_pixel_ratio": {
                "value": round(optimal_white_ratio, 4) if optimal_white_ratio else 0.95,
                "accuracy": white_acc,
                "justification": white_just,
                "distribution": {
                    "blank_p5": round(np.percentile(blank_white_ratios, 5), 4)
                    if blank_white_ratios
                    else None,
                    "non_blank_p95": round(np.percentile(non_blank_white_ratios, 95), 4)
                    if non_blank_white_ratios
                    else None,
                },
            },
        }

        if optimal_edge_count is not None:
            recommendations["edge_threshold"] = {
                "value": int(optimal_edge_count),
                "accuracy": edge_acc,
                "justification": edge_just,
                "distribution": {
                    "blank_p95": int(np.percentile(blank_edge_counts, 95))
                    if blank_edge_counts
                    else None,
                    "non_blank_p5": int(np.percentile(non_blank_edge_counts, 5))
                    if non_blank_edge_counts
                    else None,
                },
            }

        # Calculate overall confidence
        accuracies = [var_acc, white_acc]
        if optimal_edge_count is not None:
            accuracies.append(edge_acc)

        avg_accuracy = np.mean(accuracies)
        recommendations["overall_confidence"] = round(avg_accuracy, 3)

        return recommendations

    def generate_config(self, recommendations: Dict, output_path: str = None) -> None:
        """
        Generate optimized configuration file.

        Args:
            recommendations: Dictionary of optimized parameters
            output_path: Path to save config file (default: config/optimized_config.json)
        """
        if output_path is None:
            output_path = Path("config") / "optimized_config.json"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build config structure
        config = {
            "blank_detection": {
                "variance_threshold": recommendations["variance_threshold"]["value"],
                "edge_threshold": recommendations.get("edge_threshold", {}).get(
                    "value", 50
                ),
                "white_pixel_ratio": recommendations["white_pixel_ratio"]["value"],
                "use_edge_detection": True,
                "canny_low": 50,
                "canny_high": 150,
            },
            "optimization_metadata": {
                "overall_confidence": recommendations["overall_confidence"],
                "sample_count": {
                    "blank": len(self.blank_samples),
                    "non_blank": len(self.non_blank_samples),
                },
                "parameter_details": recommendations,
            },
        }

        # Save config
        with open(output_path, "w") as f:
            json.dump(config, f, indent=2)

        logger.info(f"Optimized config saved to: {output_path}")

    def generate_report(self, stats: Dict, recommendations: Dict) -> str:
        """
        Generate a human-readable optimization report.

        Args:
            stats: Distribution statistics
            recommendations: Optimized parameters

        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 70)
        report.append("BLANK PAGE DETECTION - PARAMETER OPTIMIZATION REPORT")
        report.append("=" * 70)
        report.append("")

        # Sample summary
        report.append("SAMPLE SUMMARY")
        report.append("-" * 70)
        report.append(f"Total samples: {len(self.samples)}")
        report.append(f"  Blank pages: {len(self.blank_samples)}")
        report.append(f"  Non-blank pages: {len(self.non_blank_samples)}")
        report.append("")

        # Overall confidence
        report.append("OPTIMIZATION RESULTS")
        report.append("-" * 70)
        confidence = recommendations["overall_confidence"]
        report.append(
            f"Overall Confidence: {confidence:.1%} "
            f"({'HIGH' if confidence > 0.9 else 'MEDIUM' if confidence > 0.75 else 'LOW'})"
        )
        report.append("")

        # Variance threshold
        report.append("1. VARIANCE THRESHOLD")
        var_rec = recommendations["variance_threshold"]
        report.append(f"   Recommended value: {var_rec['value']}")
        report.append(f"   Accuracy: {var_rec['accuracy']:.1%}")
        report.append(f"   {var_rec['justification']}")
        if stats.get("blank", {}).get("variance"):
            report.append(
                f"   Blank pages variance: {stats['blank']['variance']['min']:.2f} - "
                f"{stats['blank']['variance']['max']:.2f} (median: {stats['blank']['variance']['median']:.2f})"
            )
        if stats.get("non_blank", {}).get("variance"):
            report.append(
                f"   Non-blank variance: {stats['non_blank']['variance']['min']:.2f} - "
                f"{stats['non_blank']['variance']['max']:.2f} (median: {stats['non_blank']['variance']['median']:.2f})"
            )
        report.append("")

        # White pixel ratio
        report.append("2. WHITE PIXEL RATIO")
        white_rec = recommendations["white_pixel_ratio"]
        report.append(f"   Recommended value: {white_rec['value']:.4f} ({white_rec['value']:.1%})")
        report.append(f"   Accuracy: {white_rec['accuracy']:.1%}")
        report.append(f"   {white_rec['justification']}")
        if stats.get("blank", {}).get("white_ratio"):
            report.append(
                f"   Blank pages white ratio: {stats['blank']['white_ratio']['min']:.1%} - "
                f"{stats['blank']['white_ratio']['max']:.1%} (median: {stats['blank']['white_ratio']['median']:.1%})"
            )
        if stats.get("non_blank", {}).get("white_ratio"):
            report.append(
                f"   Non-blank white ratio: {stats['non_blank']['white_ratio']['min']:.1%} - "
                f"{stats['non_blank']['white_ratio']['max']:.1%} (median: {stats['non_blank']['white_ratio']['median']:.1%})"
            )
        report.append("")

        # Edge threshold
        if "edge_threshold" in recommendations:
            report.append("3. EDGE COUNT THRESHOLD")
            edge_rec = recommendations["edge_threshold"]
            report.append(f"   Recommended value: {edge_rec['value']}")
            report.append(f"   Accuracy: {edge_rec['accuracy']:.1%}")
            report.append(f"   {edge_rec['justification']}")
            if stats.get("blank", {}).get("edge_count"):
                report.append(
                    f"   Blank pages edge count: {stats['blank']['edge_count']['min']} - "
                    f"{stats['blank']['edge_count']['max']} (median: {stats['blank']['edge_count']['median']:.0f})"
                )
            if stats.get("non_blank", {}).get("edge_count"):
                report.append(
                    f"   Non-blank edge count: {stats['non_blank']['edge_count']['min']} - "
                    f"{stats['non_blank']['edge_count']['max']} (median: {stats['non_blank']['edge_count']['median']:.0f})"
                )
            report.append("")

        # Recommendations
        report.append("NEXT STEPS")
        report.append("-" * 70)
        report.append("1. Review the optimized parameters in config/optimized_config.json")
        report.append("2. Run validation: python tools/validate_parameters.py")
        report.append(
            "3. If satisfied, update config/config.py with the new parameters"
        )
        report.append(
            "4. Alternatively, use interactive tuner for fine-tuning: python tools/interactive_tuner.py"
        )
        report.append("")
        report.append("=" * 70)

        return "\n".join(report)

    def plot_distributions(self, save_path: str = None) -> None:
        """
        Create visualization plots of metric distributions.

        Args:
            save_path: Optional path to save the plot
        """
        logger.info("Generating distribution plots...")

        # Prepare data
        blank_variances = [s["metrics"]["variance"] for s in self.blank_samples]
        non_blank_variances = [s["metrics"]["variance"] for s in self.non_blank_samples]

        blank_white_ratios = [s["metrics"]["white_ratio"] for s in self.blank_samples]
        non_blank_white_ratios = [
            s["metrics"]["white_ratio"] for s in self.non_blank_samples
        ]

        blank_edge_counts = [
            s["metrics"]["edge_count"]
            for s in self.blank_samples
            if s["metrics"]["edge_count"] is not None
        ]
        non_blank_edge_counts = [
            s["metrics"]["edge_count"]
            for s in self.non_blank_samples
            if s["metrics"]["edge_count"] is not None
        ]

        # Create figure
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(
            "Blank vs Non-Blank Page Metric Distributions", fontsize=16, weight="bold"
        )

        # Plot 1: Variance histogram
        ax = axes[0, 0]
        if blank_variances:
            ax.hist(
                blank_variances,
                bins=30,
                alpha=0.6,
                label="Blank",
                color="lightblue",
                edgecolor="black",
            )
        if non_blank_variances:
            ax.hist(
                non_blank_variances,
                bins=30,
                alpha=0.6,
                label="Non-Blank",
                color="lightcoral",
                edgecolor="black",
            )
        ax.set_xlabel("Variance")
        ax.set_ylabel("Frequency")
        ax.set_title("Pixel Variance Distribution")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Plot 2: White ratio histogram
        ax = axes[0, 1]
        if blank_white_ratios:
            ax.hist(
                blank_white_ratios,
                bins=30,
                alpha=0.6,
                label="Blank",
                color="lightblue",
                edgecolor="black",
            )
        if non_blank_white_ratios:
            ax.hist(
                non_blank_white_ratios,
                bins=30,
                alpha=0.6,
                label="Non-Blank",
                color="lightcoral",
                edgecolor="black",
            )
        ax.set_xlabel("White Pixel Ratio")
        ax.set_ylabel("Frequency")
        ax.set_title("White Pixel Ratio Distribution")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Plot 3: Edge count histogram
        ax = axes[1, 0]
        if blank_edge_counts and non_blank_edge_counts:
            ax.hist(
                blank_edge_counts,
                bins=30,
                alpha=0.6,
                label="Blank",
                color="lightblue",
                edgecolor="black",
            )
            ax.hist(
                non_blank_edge_counts,
                bins=30,
                alpha=0.6,
                label="Non-Blank",
                color="lightcoral",
                edgecolor="black",
            )
            ax.set_xlabel("Edge Count")
            ax.set_ylabel("Frequency")
            ax.set_title("Edge Count Distribution")
            ax.legend()
            ax.grid(True, alpha=0.3)
        else:
            ax.text(
                0.5,
                0.5,
                "Edge count data not available",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            ax.set_title("Edge Count Distribution")

        # Plot 4: Box plots comparison
        ax = axes[1, 1]
        data_to_plot = []
        labels = []
        if blank_variances:
            data_to_plot.append(blank_variances)
            labels.append("Blank\nVariance")
        if non_blank_variances:
            data_to_plot.append(non_blank_variances)
            labels.append("Non-Blank\nVariance")

        if data_to_plot:
            bp = ax.boxplot(data_to_plot, labels=labels, patch_artist=True)
            for patch, color in zip(
                bp["boxes"], ["lightblue", "lightcoral"][: len(data_to_plot)]
            ):
                patch.set_facecolor(color)
            ax.set_ylabel("Variance")
            ax.set_title("Variance Comparison (Box Plot)")
            ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            logger.info(f"Distribution plot saved to: {save_path}")
        else:
            plt.show()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Optimize blank detection parameters using labeled samples"
    )
    parser.add_argument(
        "--samples-dir",
        type=str,
        default="samples",
        help="Directory containing samples and metrics.json",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="config/optimized_config.json",
        help="Path to save optimized config",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Generate distribution plots",
    )
    parser.add_argument(
        "--plot-output",
        type=str,
        default="samples/distributions.png",
        help="Path to save distribution plot",
    )

    args = parser.parse_args()

    try:
        optimizer = ParameterOptimizer(samples_dir=args.samples_dir)

        # Analyze distributions
        stats = optimizer.analyze_distributions()

        # Optimize parameters
        recommendations = optimizer.optimize_parameters()

        # Generate config
        optimizer.generate_config(recommendations, output_path=args.output)

        # Generate and print report
        report = optimizer.generate_report(stats, recommendations)
        print("\n" + report)

        # Generate plots if requested
        if args.plot:
            optimizer.plot_distributions(save_path=args.plot_output)

    except Exception as e:
        logger.error(f"Error during optimization: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
