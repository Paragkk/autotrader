#!/usr/bin/env python3
"""
Demonstration of pathlib improvements for uv-managed projects
"""

from pathlib import Path
from src.infra.config import load_config, resolve_config_path
from src.infra.path_utils import (
    get_project_root,
    get_data_dir,
    get_logs_dir,
    resolve_project_path,
    is_uv_project,
    get_env_path,
)


def demonstrate_path_improvements():
    """Demonstrate the path handling improvements."""
    print("=== Path Handling Improvements for uv-managed Projects ===\n")

    # Project detection
    print("1. Project Detection:")
    print(f"   Project root: {get_project_root()}")
    print(f"   Is uv project: {is_uv_project()}")
    print(f"   Data directory: {get_data_dir()}")
    print(f"   Logs directory: {get_logs_dir()}")
    print()

    # Configuration path resolution
    print("2. Configuration Path Resolution:")

    # Test different scenarios
    test_configs = [
        None,  # Default
        "config.yaml",  # Relative to project root
        "config/production.yaml",  # Relative path
        Path("config.yaml"),  # Path object
    ]

    for config_path in test_configs:
        resolved = resolve_config_path(config_path)
        print(f"   {config_path} -> {resolved}")
        print(f"   Exists: {resolved.exists()}")
    print()

    # Environment-based path resolution
    print("3. Environment-based Path Resolution:")
    import os

    # Temporarily set env var for demo
    os.environ["TRADING_DATA_DIR"] = "data/trading"
    data_path = get_env_path("TRADING_DATA_DIR", "data/default", "root")
    print(f"   TRADING_DATA_DIR -> {data_path}")

    # Clean up
    del os.environ["TRADING_DATA_DIR"]
    print()

    # Path utilities
    print("4. Path Utilities:")
    relative_paths = [
        ("logs/app.log", "logs"),
        ("data/stocks.csv", "data"),
        ("config/secrets.yaml", "config"),
    ]

    for path, relative_to in relative_paths:
        resolved = resolve_project_path(path, relative_to)
        print(f"   {path} (relative to {relative_to}) -> {resolved}")
    print()

    # Configuration loading
    print("5. Configuration Loading:")
    try:
        config = load_config()
        print(f"   Loaded config keys: {list(config.keys())}")
        print(f"   Broker: {config.get('broker', 'Not set')}")
        print(f"   Use paper trading: {config.get('use_paper_trading', 'Not set')}")
    except Exception as e:
        print(f"   Error loading config: {e}")
    print()

    # Benefits summary
    print("6. Benefits of These Improvements:")
    print("   ✓ Automatic project root detection (works with uv)")
    print("   ✓ Cross-platform path handling")
    print("   ✓ Environment variable overrides")
    print("   ✓ Type-safe path operations")
    print("   ✓ Robust error handling")
    print("   ✓ Consistent path resolution")
    print("   ✓ Easy testing and deployment")


if __name__ == "__main__":
    demonstrate_path_improvements()
