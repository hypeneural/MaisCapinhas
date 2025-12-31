from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from people_analytics.storage.paths import VideoPathInfo, parse_video_path


def scan_videos(root: Path, extensions: Sequence[str] | None = None) -> Iterable[VideoPathInfo]:
    exts = {e.lower() for e in (extensions or [".mp4", ".mkv", ".avi"])}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in exts:
            continue
        try:
            yield parse_video_path(path, root)
        except Exception:
            continue
