"""
Path utilities for uv-managed projects
"""

from pathlib import Path
from typing import Optional, Union
import os


def get_project_root() -> Path:
    """
    Get the project root directory by looking for pyproject.toml file.
    This is the standard way to detect project root in uv-managed projects.
    """
    current_path = Path(__file__).resolve()

    # Look for pyproject.toml in current directory and parent directories
    for parent in [current_path] + list(current_path.parents):
        if (parent / "pyproject.toml").exists():
            return parent

    # Fallback to the directory containing this file's parent's parent
    return current_path.parent.parent.parent


def get_src_root() -> Path:
    """Get the src directory root."""
    return get_project_root() / "src"


def get_data_dir() -> Path:
    """Get the data directory, creating it if it doesn't exist."""
    data_dir = get_project_root() / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_logs_dir() -> Path:
    """Get the logs directory, creating it if it doesn't exist."""
    logs_dir = get_project_root() / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


def get_config_dir() -> Path:
    """Get the config directory."""
    return get_project_root() / "config"


def resolve_project_path(path: Union[str, Path], relative_to: str = "root") -> Path:
    """
    Resolve a path relative to different project directories.

    Args:
        path: The path to resolve
        relative_to: Base directory ('root', 'src', 'data', 'logs', 'config')

    Returns:
        Resolved absolute Path
    """
    path = Path(path)

    # If already absolute, return as-is
    if path.is_absolute():
        return path

    # Get the base directory
    base_dirs = {
        "root": get_project_root(),
        "src": get_src_root(),
        "data": get_data_dir(),
        "logs": get_logs_dir(),
        "config": get_config_dir(),
    }

    base_dir = base_dirs.get(relative_to, get_project_root())
    return base_dir / path


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to create

    Returns:
        Path object for the created directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_env_path(
    env_var: str, default: Union[str, Path], relative_to: str = "root"
) -> Path:
    """
    Get a path from environment variable with fallback to default.

    Args:
        env_var: Environment variable name
        default: Default path if env var not set
        relative_to: Base directory for relative paths

    Returns:
        Resolved Path object
    """
    env_value = os.getenv(env_var)
    if env_value:
        return resolve_project_path(env_value, relative_to)
    return resolve_project_path(default, relative_to)


def safe_path_join(*parts: Union[str, Path]) -> Path:
    """
    Safely join path parts, handling both string and Path objects.

    Args:
        parts: Path parts to join

    Returns:
        Joined Path object
    """
    if not parts:
        return Path()

    result = Path(parts[0])
    for part in parts[1:]:
        result = result / part
    return result


def is_uv_project() -> bool:
    """Check if current directory is a uv-managed project."""
    return (get_project_root() / "uv.lock").exists()


def get_uv_cache_dir() -> Optional[Path]:
    """Get the uv cache directory if available."""
    if not is_uv_project():
        return None

    # Check common uv cache locations
    cache_dirs = [
        Path.home() / ".cache" / "uv",
        Path.home() / "Library" / "Caches" / "uv",  # macOS
        Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache")) / "uv",
    ]

    for cache_dir in cache_dirs:
        if cache_dir.exists():
            return cache_dir

    return None


def get_virtual_env_path() -> Optional[Path]:
    """Get the virtual environment path if available."""
    venv_path = os.getenv("VIRTUAL_ENV")
    if venv_path:
        return Path(venv_path)

    # Check for .venv in project root (common uv pattern)
    project_venv = get_project_root() / ".venv"
    if project_venv.exists():
        return project_venv

    return None
