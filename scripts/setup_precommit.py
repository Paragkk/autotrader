#!/usr/bin/env python3
"""
Setup script for pre-commit hooks using UV
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status"""
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout.strip():
            pass
        return True
    except subprocess.CalledProcessError:
        return False


def main() -> int:
    """Main setup function"""

    # Change to project root
    Path(__file__).parent.parent

    commands = [
        (["uv", "sync", "--dev"], "Installing dev dependencies"),
        (["uv", "run", "pre-commit", "install"], "Installing pre-commit hooks"),
        (
            ["uv", "run", "pre-commit", "run", "--all-files"],
            "Running pre-commit on all files",
        ),
    ]

    success = True
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            success = False
            if "pre-commit run" not in desc:  # Allow failures on the initial run
                break

    if success:
        pass
    else:
        pass

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
