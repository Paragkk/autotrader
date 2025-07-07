#!/usr/bin/env python3
"""
Setup script for pre-commit hooks using UV
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Success")
        if result.stdout.strip():
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed")
        print(f"   Error: {e.stderr.strip() if e.stderr else str(e)}")
        return False


def main():
    """Main setup function"""
    print("🚀 Setting up pre-commit hooks with UV...")

    # Change to project root
    project_root = Path(__file__).parent.parent
    print(f"📁 Working in: {project_root}")

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
        print("\n🎉 Pre-commit setup complete!")
        print("💡 Now when you commit, ruff will automatically check your code.")
        print("🔧 To manually run checks: uv run pre-commit run --all-files")
    else:
        print("\n⚠️  Setup completed with some issues. Check the output above.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
