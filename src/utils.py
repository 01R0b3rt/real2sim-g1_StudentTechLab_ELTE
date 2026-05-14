from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "g1_arm_mapping.yaml"


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file and return an empty dict for empty documents."""
    try:
        import yaml
    except ImportError as exc:
        print_dependency_help("PyYAML")
        raise exc

    yaml_path = resolve_path(path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"Config file not found: {yaml_path}")
    with yaml_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a YAML mapping: {yaml_path}")
    return data


def resolve_path(path: str | Path | None, base_dir: str | Path | None = None) -> Path:
    """Resolve project-relative paths without hardcoding local absolute paths."""
    if path is None:
        return PROJECT_ROOT
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    base = Path(base_dir).expanduser() if base_dir is not None else PROJECT_ROOT
    if not base.is_absolute():
        base = PROJECT_ROOT / base
    return (base / candidate).resolve()


def parse_camera_source(value: Any) -> int | str:
    """Convert CLI/YAML camera values into OpenCV-compatible sources."""
    if isinstance(value, int):
        return value
    text = str(value)
    if text.isdigit():
        return int(text)
    return text


def package_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def dependency_status() -> dict[str, bool]:
    packages = ["cv2", "mediapipe", "mujoco", "yaml", "numpy"]
    return {name: package_available(name) for name in packages}


def print_dependency_help(package: str) -> None:
    install = "pip install -r requirements.txt"
    if package == "mediapipe":
        print(
            "MediaPipe is not installed. Install project dependencies with:\n"
            f"  {install}\n"
            "If you are on a new Python version, use Python 3.10 or 3.11 for "
            "the broadest MediaPipe wheel support."
        )
    elif package == "mujoco":
        print(
            "MuJoCo is not installed. Install project dependencies with:\n"
            f"  {install}\n"
            "The Python package is required even if the Unitree XML assets are "
            "already downloaded."
        )
    else:
        print(f"{package} is not installed. Install dependencies with: {install}")


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def project_python_command(*args: str) -> list[str]:
    """Build a command that uses the current interpreter from the project root."""
    return [sys.executable, *args]
