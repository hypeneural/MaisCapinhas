from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_stores_config(config_dir: str) -> dict[str, dict]:
    data = load_yaml(Path(config_dir) / "stores.yml")
    stores = data.get("stores", [])
    return {s.get("code"): s for s in stores}


def load_shifts_config(config_dir: str) -> dict:
    return load_yaml(Path(config_dir) / "shifts.yml")


def load_camera_config(config_dir: str, store_code: str, camera_code: str) -> dict:
    filename = f"store_{store_code}_{camera_code}.yml"
    path = Path(config_dir) / "cameras" / filename
    return load_yaml(path)
