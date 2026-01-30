"""Entry point for running Blink! as a module."""

import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from blink.app import main


def cli_main() -> int:
    """CLI entry point with argument parsing.

    Returns:
        Exit code.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Blink! - Eye Health Monitor")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()
    return main(debug=args.debug)


if __name__ == "__main__":
    sys.exit(cli_main())
