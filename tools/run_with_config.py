"""
Run PDF Processing with Different Configurations

This script provides an easy way to run the main processing pipeline
with different parameter configurations (current, optimized, or tuned)
without modifying the main config file.
"""

import argparse
import json
import logging
import sys
import subprocess
from pathlib import Path
from typing import Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import get_config, BLANK_DETECTION_CONFIG

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class ConfigRunner:
    """Runs PDF processing with different configurations."""

    AVAILABLE_CONFIGS = {
        "current": {
            "path": None,  # Uses default from config.py
            "description": "Current default configuration from config/config.py",
        },
        "optimized": {
            "path": "config/optimized_config.json",
            "description": "Automatically optimized parameters from sample analysis",
        },
        "tuned": {
            "path": "config/tuned_config.json",
            "description": "Manually tuned parameters from interactive tuner",
        },
    }

    def __init__(self):
        """Initialize the config runner."""
        self.base_dir = Path(__file__).parent.parent
        self.main_script = self.base_dir / "main.py"

    def get_config(self, config_name: str) -> Optional[Dict]:
        """
        Get configuration by name.

        Args:
            config_name: Name of the config (current, optimized, tuned) or path to JSON file

        Returns:
            Configuration dictionary or None if not found
        """
        # Check if it's a predefined config name
        if config_name in self.AVAILABLE_CONFIGS:
            config_info = self.AVAILABLE_CONFIGS[config_name]

            if config_name == "current":
                # Return current default config
                return get_config()
            else:
                config_path = self.base_dir / config_info["path"]
                if not config_path.exists():
                    logger.error(
                        f"Configuration file not found: {config_path}\n"
                        f"Run the appropriate optimization tool first."
                    )
                    return None

                with open(config_path, "r") as f:
                    return json.load(f)

        # Otherwise treat as file path
        else:
            config_path = Path(config_name)
            if not config_path.exists():
                logger.error(f"Configuration file not found: {config_path}")
                return None

            with open(config_path, "r") as f:
                return json.load(f)

    def show_config_info(self, config_name: str) -> None:
        """
        Display information about a configuration.

        Args:
            config_name: Name of the config or path to config file
        """
        print("\n" + "=" * 70)
        print(f"CONFIGURATION: {config_name}")
        print("=" * 70)

        config = self.get_config(config_name)
        if not config:
            return

        # Show blank detection parameters
        if "blank_detection" in config:
            params = config["blank_detection"]
        else:
            params = config

        print("\nBlank Detection Parameters:")
        print(f"  Variance Threshold:   {params.get('variance_threshold', 'N/A')}")
        print(f"  Edge Threshold:       {params.get('edge_threshold', 'N/A')}")
        print(
            f"  White Pixel Ratio:    {params.get('white_pixel_ratio', 'N/A')} "
            f"({params.get('white_pixel_ratio', 0) * 100:.1f}%)"
        )
        print(f"  Use Edge Detection:   {params.get('use_edge_detection', 'N/A')}")
        print(f"  Canny Low:            {params.get('canny_low', 'N/A')}")
        print(f"  Canny High:           {params.get('canny_high', 'N/A')}")

        # Show metadata if available
        if "optimization_metadata" in config:
            meta = config["optimization_metadata"]
            print("\nOptimization Metadata:")
            print(f"  Overall Confidence:   {meta.get('overall_confidence', 'N/A'):.1%}")
            if "sample_count" in meta:
                print(
                    f"  Sample Count:         {meta['sample_count']['blank']} blank, "
                    f"{meta['sample_count']['non_blank']} non-blank"
                )

        if "tuning_metadata" in config:
            meta = config["tuning_metadata"]
            print("\nTuning Metadata:")
            print(f"  Samples Used:         {meta.get('samples_used', 'N/A')}")
            if "performance" in meta:
                perf = meta["performance"]
                print(f"  Accuracy:             {perf.get('accuracy', 0):.1%}")
                print(f"  F1-Score:             {perf.get('f1_score', 0):.3f}")

        print("=" * 70 + "\n")

    def list_available_configs(self) -> None:
        """List all available configurations."""
        print("\n" + "=" * 70)
        print("AVAILABLE CONFIGURATIONS")
        print("=" * 70 + "\n")

        for name, info in self.AVAILABLE_CONFIGS.items():
            status = "✓" if name == "current" else "✗"

            if name != "current":
                config_path = self.base_dir / info["path"]
                status = "✓" if config_path.exists() else "✗"

            print(f"{status} {name:12s} - {info['description']}")

            if status == "✗" and name != "current":
                print(f"             File: {info['path']} (not found)")

        print("\n" + "=" * 70 + "\n")

    def run_processing(
        self,
        config_name: str,
        input_pdf: str,
        output_dir: str,
        verbose: bool = False,
    ) -> int:
        """
        Run the main processing pipeline with specified configuration.

        Args:
            config_name: Name of config or path to config file
            input_pdf: Path to input PDF file
            output_dir: Path to output directory
            verbose: Enable verbose logging

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        logger.info(f"Running PDF processing with '{config_name}' configuration")

        # Get config
        config = self.get_config(config_name)
        if not config:
            return 1

        # Show config info
        self.show_config_info(config_name)

        # Prepare command
        cmd = [sys.executable, str(self.main_script), "--input", input_pdf, "--output", output_dir]

        # Add config file if not using current default
        if config_name != "current":
            # Create temporary config file for main.py
            temp_config = self.base_dir / "config" / "temp_run_config.json"
            temp_config.parent.mkdir(parents=True, exist_ok=True)

            with open(temp_config, "w") as f:
                json.dump(config, f, indent=2)

            cmd.extend(["--config", str(temp_config)])

        # Add verbose flag
        if verbose:
            cmd.append("--verbose")

        # Run the processing
        logger.info(f"Executing: {' '.join(cmd)}")
        print("\n" + "=" * 70)
        print("PROCESSING OUTPUT")
        print("=" * 70 + "\n")

        try:
            result = subprocess.run(cmd, check=False)
            return result.returncode

        except Exception as e:
            logger.error(f"Error running processing: {e}")
            return 1

        finally:
            # Clean up temp config
            if config_name != "current":
                temp_config = self.base_dir / "config" / "temp_run_config.json"
                if temp_config.exists():
                    temp_config.unlink()

    def compare_configs(self, config_names: list) -> None:
        """
        Compare multiple configurations side by side.

        Args:
            config_names: List of config names or paths to compare
        """
        configs_data = {}

        # Load all configs
        for name in config_names:
            config = self.get_config(name)
            if config:
                configs_data[name] = config

        if not configs_data:
            logger.error("No valid configurations to compare")
            return

        print("\n" + "=" * 90)
        print("CONFIGURATION COMPARISON")
        print("=" * 90 + "\n")

        # Header
        print(f"{'Parameter':<25}", end="")
        for name in configs_data.keys():
            print(f"{name[:20]:>20}", end="")
        print()
        print("-" * 90)

        # Parameters to compare
        params_to_compare = [
            ("variance_threshold", "Variance Threshold"),
            ("edge_threshold", "Edge Threshold"),
            ("white_pixel_ratio", "White Pixel Ratio"),
            ("use_edge_detection", "Use Edge Detection"),
            ("canny_low", "Canny Low"),
            ("canny_high", "Canny High"),
        ]

        for param_key, param_label in params_to_compare:
            print(f"{param_label:<25}", end="")

            for name, config in configs_data.items():
                # Get blank detection params
                if "blank_detection" in config:
                    params = config["blank_detection"]
                else:
                    params = config

                value = params.get(param_key, "N/A")

                # Format value
                if param_key == "white_pixel_ratio" and isinstance(value, (int, float)):
                    formatted = f"{value:.4f} ({value*100:.1f}%)"
                else:
                    formatted = str(value)

                print(f"{formatted:>20}", end="")
            print()

        print("\n" + "=" * 90 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run PDF processing with different configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with optimized config
  python tools/run_with_config.py --config optimized --input input/report.pdf --output output/

  # Run with tuned config
  python tools/run_with_config.py --config tuned --input input/report.pdf --output output/

  # Run with custom config file
  python tools/run_with_config.py --config my_config.json --input input/report.pdf --output output/

  # List available configs
  python tools/run_with_config.py --list

  # Show info about a config
  python tools/run_with_config.py --info optimized

  # Compare configurations
  python tools/run_with_config.py --compare current optimized tuned
        """,
    )

    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Config to use: 'current', 'optimized', 'tuned', or path to JSON file",
    )

    parser.add_argument(
        "--input", "-i", type=str, help="Path to input PDF file"
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="output",
        help="Path to output directory (default: output)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    parser.add_argument(
        "--list", "-l", action="store_true", help="List available configurations"
    )

    parser.add_argument(
        "--info", type=str, help="Show detailed info about a configuration"
    )

    parser.add_argument(
        "--compare",
        nargs="+",
        help="Compare multiple configurations (provide config names/paths)",
    )

    args = parser.parse_args()

    runner = ConfigRunner()

    # List configs
    if args.list:
        runner.list_available_configs()
        return 0

    # Show config info
    if args.info:
        runner.show_config_info(args.info)
        return 0

    # Compare configs
    if args.compare:
        runner.compare_configs(args.compare)
        return 0

    # Run processing
    if args.config and args.input:
        exit_code = runner.run_processing(
            args.config, args.input, args.output, args.verbose
        )
        return exit_code

    # No valid action specified
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
