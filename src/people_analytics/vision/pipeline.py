from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from people_analytics.storage.paths import VideoPathInfo
from people_analytics.vision.video_reader import VideoReader
from people_analytics.vision.stages.detect_people import DetectPeopleStage
from people_analytics.vision.stages.track_people import TrackPeopleStage
from people_analytics.vision.stages.count_line import CountLineStage
from people_analytics.vision.stages.staff_exclusion import StaffExclusionStage


@dataclass
class PipelineResult:
    events: list[dict] = field(default_factory=list)
    presence_samples: list[dict] = field(default_factory=list)
    frames_read: int = 0
    duration_s: float | None = None
    errors: list[str] = field(default_factory=list)

    def summarize_counts(self) -> dict:
        counts = {"in": 0, "out": 0, "staff_in": 0, "staff_out": 0}
        for event in self.events:
            direction = event.get("direction")
            is_staff = event.get("is_staff", False)
            if direction == "IN":
                counts["in"] += 1
                if is_staff:
                    counts["staff_in"] += 1
            elif direction == "OUT":
                counts["out"] += 1
                if is_staff:
                    counts["staff_out"] += 1
        return counts

    def to_output(self, info: VideoPathInfo, tz_name: str | None = None) -> dict:
        start_dt, end_dt = info.to_datetime_range()
        if tz_name:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo(tz_name)
            start_dt = start_dt.replace(tzinfo=tz)
            end_dt = end_dt.replace(tzinfo=tz)
        return {
            "segment": {
                "store_code": info.store_code,
                "camera_code": info.camera_code,
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
            },
            "counts": self.summarize_counts(),
            "events": self.events,
            "presence_samples": self.presence_samples,
            "meta": {
                "frames_read": self.frames_read,
                "duration_s": self.duration_s,
                "errors": self.errors,
            },
        }


class Pipeline:
    def __init__(self, stages: list, target_fps: int | None = None):
        self.stages = stages
        self.reader = VideoReader(target_fps=target_fps)

    def run(self, path: Path) -> PipelineResult:
        result = PipelineResult()
        context = {"result": result, "now": datetime.now(timezone.utc)}
        last_ts = None

        for stage in self.stages:
            stage.setup(context)

        try:
            for frame, ts in self.reader.iter_frames(path):
                context["frame"] = frame
                context["ts"] = ts
                last_ts = ts
                for stage in self.stages:
                    stage.on_frame(context)
                result.frames_read += 1
        except Exception as exc:
            result.errors.append(str(exc))

        for stage in self.stages:
            stage.on_finish(context)

        if last_ts is not None:
            result.duration_s = last_ts

        return result


def build_pipeline(camera_cfg: dict) -> Pipeline:
    target_fps = None
    if camera_cfg.get("processing"):
        target_fps = camera_cfg["processing"].get("target_fps")

    stages = [
        DetectPeopleStage(camera_cfg),
        TrackPeopleStage(camera_cfg),
        CountLineStage(camera_cfg),
        StaffExclusionStage(camera_cfg),
    ]
    return Pipeline(stages=stages, target_fps=target_fps)
