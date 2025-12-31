from __future__ import annotations

from pathlib import Path

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    cv2 = None


class VideoReader:
    def __init__(self, target_fps: int | None = None):
        self.target_fps = target_fps

    def iter_frames(self, path: Path):
        if cv2 is None:
            raise RuntimeError("opencv-not-installed")
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise RuntimeError("cannot-open-video")
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        step = 1
        if self.target_fps and fps:
            step = max(1, int(round(fps / self.target_fps)))

        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % step == 0:
                ts_ms = cap.get(cv2.CAP_PROP_POS_MSEC) or 0
                yield frame, ts_ms / 1000.0
            idx += 1
        cap.release()
