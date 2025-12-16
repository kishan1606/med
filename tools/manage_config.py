"""
Configuration Manager for Blank Page Detection

This script helps you manage, view, backup, and deploy different
blank detection configurations.
"""

import argparse
import json
import logging
import sys
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages blank detection configurations."""

    def __init__(self):
        """Initialize the config manager."""
        self.base_dir = Path(__file__).parent.parent
        self.config_dir = self.base_dir / "config"
        self.config_file = self.config_dir / "config.py"
        self.backup_dir = self.config_dir / "backups"

        self.available_configs = {
            "optimized": self.config_dir / "optimized_config.json",
            "tuned": self.config_dir / "tuned_config.json",
        }

    def show_current_config(self) -> None:
        """Display the current active configuration from config.py."""
        print("\n" + "=" * 70)
        print("CURRENT ACTIVE CONFIGURATION (config/config.py)")
        print("=" * 70 + "\n")

        try:
            from config.config import BLANK_DETECTION_CONFIG

            params = BLANK_DETECTION_CONFIG

            print("Blank Detection Parameters:")
            print(f"  Variance Threshold:   {params.get('variance_threshold', 'N/A')}")
            print(f"  Edge Threshold:       {params.get('edge_threshold', 'N/A')}")
            print(
                f"  White Pixel Ratio:    {params.get('white_pixel_ratio', 'N/A')} "
                f"({params.get('white_pixel_ratio', 0) * 100:.1f}%)"
            )
            print(f"  Use Edge Detection:   {params.get('use_edge_detection', 'N/A')}")
            print(f"  Canny Low:            {params.get('canny_low', 'N/A')}")
            print(f"  Canny High:           {params.get('canny_high', 'N/A')}")

            print("\n" + "=" * 70 + "\n")

        except Exception as e:
            logger.error(f"Error reading current config: {e}")

    def show_config(self, config_path: Path, name: str = None) -> None:
        """
        Display a configuration file.

        Args:
            config_path: Path to config JSON file
            name: Optional name for display
        """
        if not config_path.exists():
            logger.warning(f"Configuration not found: {config_path}")
            return

        print("\n" + "=" * 70)
        print(f"CONFIGURATION: {name or config_path.name}")
        print(f"File: {config_path}")
        print("=" * 70 + "\n")

        try:
            with open(config_path, "r") as f:
                config = json.load(f)

            # Get blank detection params
            if "blank_detection" in config:
                params = config["blank_detection"]
            else:
                params = config

            print("Blank Detection Parameters:")
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
                    print(f"  Precision:            {perf.get('precision', 0):.1%}")
                    print(f"  Recall:               {perf.get('recall', 0):.1%}")
                    print(f"  F1-Score:             {perf.get('f1_score', 0):.3f}")

            print("=" * 70 + "\n")

        except Exception as e:
            logger.error(f"Error reading config: {e}")

    def list_configs(self) -> None:
        """List all available configurations."""
        print("\n" + "=" * 70)
        print("AVAILABLE CONFIGURATIONS")
        print("=" * 70 + "\n")

        # Current config
        print("✓ current     - Active configuration in config/config.py")

        # Optimized config
        optimized = self.available_configs["optimized"]
        status = "✓" if optimized.exists() else "✗"
        print(f"{status} optimized   - Auto-optimized from sample analysis")
        if not optimized.exists():
            print(f"              File: {optimized.relative_to(self.base_dir)} (not found)")
            print("              Run: python tools/optimize_parameters.py")

        # Tuned config
        tuned = self.available_configs["tuned"]
        status = "✓" if tuned.exists() else "✗"
        print(f"{status} tuned       - Manually tuned via interactive tool")
        if not tuned.exists():
            print(f"              File: {tuned.relative_to(self.base_dir)} (not found)")
            print("              Run: python tools/interactive_tuner.py")

        print("\n" + "=" * 70 + "\n")

    def backup_current_config(self) -> Path:
        """
        Create a backup of the current config.py file.

        Returns:
            Path to the backup file
        """
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"config_backup_{timestamp}.py"

        shutil.copy2(self.config_file, backup_path)
        logger.info(f"Backup created: {backup_path}")

        return backup_path

    def deploy_config(self, config_name: str, dry_run: bool = False) -> bool:
        """
        Deploy a configuration to config/config.py.

        Args:
            config_name: Name of config to deploy ('optimized' or 'tuned')
            dry_run: If True, show what would be changed without actually deploying

        Returns:
            True if successful, False otherwise
        """
        if config_name not in self.available_configs:
            logger.error(f"Unknown config: {config_name}")
            logger.info(f"Available configs: {', '.join(self.available_configs.keys())}")
            return False

        config_path = self.available_configs[config_name]
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return False

        # Load the new config
        try:
            with open(config_path, "r") as f:
                new_config = json.load(f)

            if "blank_detection" in new_config:
                params = new_config["blank_detection"]
            else:
                params = new_config

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return False

        # Show current vs new
        print("\n" + "=" * 70)
        print(f"DEPLOYING: {config_name}")
        print("=" * 70 + "\n")

        from config.config import BLANK_DETECTION_CONFIG

        current = BLANK_DETECTION_CONFIG

        print("Parameter                 Current Value      →  New Value")
        print("-" * 70)

        changes = []
        for key in [
            "variance_threshold",
            "edge_threshold",
            "white_pixel_ratio",
            "use_edge_detection",
            "canny_low",
            "canny_high",
        ]:
            current_val = current.get(key, "N/A")
            new_val = params.get(key, "N/A")

            # Format values
            if key == "white_pixel_ratio" and isinstance(new_val, (int, float)):
                new_val_str = f"{new_val:.4f} ({new_val*100:.1f}%)"
                current_val_str = f"{current_val:.4f} ({current_val*100:.1f}%)"
            else:
                new_val_str = str(new_val)
                current_val_str = str(current_val)

            changed = "→" if current_val != new_val else " "
            print(f"{key:25} {current_val_str:>18} {changed} {new_val_str:>18}")

            if current_val != new_val:
                changes.append((key, current_val, new_val))

        print()

        if not changes:
            print("No changes to deploy - configuration is already active.")
            return True

        if dry_run:
            print("[DRY RUN] No changes made. Remove --dry-run to deploy.")
            return True

        # Confirm deployment
        print(f"This will update config/config.py with {len(changes)} parameter change(s).")
        print("A backup will be created automatically.")
        response = input("\nProceed with deployment? [y/N]: ")

        if response.lower() != "y":
            print("Deployment cancelled.")
            return False

        # Create backup
        backup_path = self.backup_current_config()
        print(f"Backup saved to: {backup_path}")

        # Update config.py
        try:
            self._update_config_file(params)
            print(f"\n✓ Configuration deployed successfully!")
            print(f"✓ {len(changes)} parameter(s) updated in config/config.py")
            print(f"\nTo revert, restore from backup: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Error deploying config: {e}")
            logger.info(f"You can manually restore from backup: {backup_path}")
            return False

    def _update_config_file(self, new_params: Dict) -> None:
        """
        Update config.py with new blank detection parameters.

        Args:
            new_params: New parameter values
        """
        # Read current config.py
        with open(self.config_file, "r") as f:
            lines = f.readlines()

        # Find and update BLANK_DETECTION_CONFIG section
        new_lines = []
        in_blank_config = False
        indent = "    "

        for i, line in enumerate(lines):
            if "BLANK_DETECTION_CONFIG = {" in line:
                in_blank_config = True
                new_lines.append(line)

                # Write new parameters
                new_lines.append(
                    f'{indent}"variance_threshold": {new_params.get("variance_threshold", 100.0)},\n'
                )
                new_lines.append(
                    f'{indent}"edge_threshold": {new_params.get("edge_threshold", 50)},\n'
                )
                new_lines.append(
                    f'{indent}"white_pixel_ratio": {new_params.get("white_pixel_ratio", 0.95)},\n'
                )
                new_lines.append(
                    f'{indent}"use_edge_detection": {str(new_params.get("use_edge_detection", True))},\n'
                )
                new_lines.append(
                    f'{indent}"canny_low": {new_params.get("canny_low", 50)},\n'
                )
                new_lines.append(
                    f'{indent}"canny_high": {new_params.get("canny_high", 150)},\n'
                )

                # Skip old parameter lines until we hit the closing brace
                continue

            elif in_blank_config:
                if line.strip() == "}":
                    in_blank_config = False
                    new_lines.append(line)
                # Skip old parameter lines
                continue

            else:
                new_lines.append(line)

        # Write updated config
        with open(self.config_file, "w") as f:
            f.writelines(new_lines)

    def list_backups(self) -> None:
        """List all config backups."""
        if not self.backup_dir.exists():
            print("\nNo backups found.")
            return

        backups = sorted(self.backup_dir.glob("config_backup_*.py"), reverse=True)

        if not backups:
            print("\nNo backups found.")
            return

        print("\n" + "=" * 70)
        print("CONFIGURATION BACKUPS")
        print("=" * 70 + "\n")

        for backup in backups:
            # Parse timestamp from filename
            timestamp_str = backup.stem.replace("config_backup_", "")
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except:
                date_str = timestamp_str

            size = backup.stat().st_size
            print(f"{date_str}  -  {backup.name}  ({size} bytes)")

        print("\n" + "=" * 70 + "\n")

    def restore_backup(self, backup_name: str) -> bool:
        """
        Restore a configuration from backup.

        Args:
            backup_name: Name of the backup file

        Returns:
            True if successful, False otherwise
        """
        backup_path = self.backup_dir / backup_name

        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_path}")
            return False

        print(f"\nRestoring backup: {backup_name}")
        print(f"This will replace config/config.py with the backup.")

        # Create a backup of current state before restoring
        current_backup = self.backup_current_config()
        print(f"Current config backed up to: {current_backup}")

        response = input("\nProceed with restore? [y/N]: ")

        if response.lower() != "y":
            print("Restore cancelled.")
            return False

        try:
            shutil.copy2(backup_path, self.config_file)
            print(f"\n✓ Configuration restored from {backup_name}")
            return True

        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage blank detection configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available configurations
  python tools/manage_config.py --list

  # Show current active config
  python tools/manage_config.py --show current

  # Show optimized config
  python tools/manage_config.py --show optimized

  # Deploy optimized config (with preview)
  python tools/manage_config.py --deploy optimized --dry-run

  # Deploy optimized config (actual deployment)
  python tools/manage_config.py --deploy optimized

  # List backups
  python tools/manage_config.py --backups

  # Restore from backup
  python tools/manage_config.py --restore config_backup_20250122_143022.py
        """,
    )

    parser.add_argument(
        "--list", "-l", action="store_true", help="List available configurations"
    )

    parser.add_argument(
        "--show",
        "-s",
        type=str,
        choices=["current", "optimized", "tuned"],
        help="Show detailed configuration",
    )

    parser.add_argument(
        "--deploy",
        "-d",
        type=str,
        choices=["optimized", "tuned"],
        help="Deploy a configuration to config/config.py",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deployment without making changes",
    )

    parser.add_argument(
        "--backups", "-b", action="store_true", help="List configuration backups"
    )

    parser.add_argument(
        "--restore", "-r", type=str, help="Restore configuration from backup file"
    )

    args = parser.parse_args()

    manager = ConfigManager()

    # List configs
    if args.list:
        manager.list_configs()
        return 0

    # Show config
    if args.show:
        if args.show == "current":
            manager.show_current_config()
        else:
            config_path = manager.available_configs.get(args.show)
            if config_path:
                manager.show_config(config_path, args.show)
        return 0

    # Deploy config
    if args.deploy:
        success = manager.deploy_config(args.deploy, dry_run=args.dry_run)
        return 0 if success else 1

    # List backups
    if args.backups:
        manager.list_backups()
        return 0

    # Restore backup
    if args.restore:
        success = manager.restore_backup(args.restore)
        return 0 if success else 1

    # No valid action
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
