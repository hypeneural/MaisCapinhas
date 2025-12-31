from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Optional

from people_analytics.core.exceptions import PathParseError

PATH_RE = re.compile(
    r"store=(?P<store>[^/\\]+)[/\\]"
    r"camera=(?P<camera>[^/\\]+)[/\\]"
    r"date=(?P<date>\d{4}-\d{2}-\d{2})[/\\]"
    r"(?P<start>\d{2}-\d{2}-\d{2})__(?P<end>\d{2}-\d{2}-\d{2})"
)


@dataclass
class VideoPathInfo:
    store_code: str
    camera_code: str
    date: date
    start_time: time
    end_time: time
    relative_path: str

    def to_datetime_range(self) -> tuple[datetime, datetime]:
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)
        return start_dt, end_dt


def parse_video_path(path: Path, video_root: Optional[Path] = None) -> VideoPathInfo:
    path_str = str(path)
    match = PATH_RE.search(path_str)
    if not match:
        raise PathParseError(f"Invalid video path: {path_str}")

    store_code = match.group("store")
    camera_code = match.group("camera")
    date_str = match.group("date")
    start_str = match.group("start").replace("-", ":")
    end_str = match.group("end").replace("-", ":")

    date_val = date.fromisoformat(date_str)
    start_time = time.fromisoformat(start_str)
    end_time = time.fromisoformat(end_str)

    if video_root:
        root_path = Path(video_root)
        try:
            relative_path = str(Path(path).relative_to(root_path))
        except ValueError:
            try:
                relative_path = str(Path(path).resolve().relative_to(root_path.resolve()))
            except ValueError:
                relative_path = str(path)
    else:
        relative_path = str(path)

    return VideoPathInfo(
        store_code=store_code,
        camera_code=camera_code,
        date=date_val,
        start_time=start_time,
        end_time=end_time,
        relative_path=relative_path,
    )
