from __future__ import annotations

from datetime import datetime, timedelta, timezone


class CountLineStage:
    def __init__(self, camera_cfg: dict):
        self.camera_cfg = camera_cfg
        line_cfg = camera_cfg.get("line", {})
        self.line_start = tuple(line_cfg.get("start", (0, 0)))
        self.line_end = tuple(line_cfg.get("end", (0, 0)))
        self.direction = camera_cfg.get("direction") or line_cfg.get("direction") or "outside_to_inside"
        self.min_interval_s = float(line_cfg.get("min_interval_s", 1.0))
        self.enabled = True
        self.track_side: dict[str, int] = {}
        self.last_cross_ts: dict[str, float] = {}

    def setup(self, context: dict) -> None:
        context["result"].events = []
        self.track_side = {}
        self.last_cross_ts = {}
        self.enabled = True
        if len(self.line_start) != 2 or len(self.line_end) != 2:
            self.enabled = False
            context["result"].errors.append("line-config-missing")

    def _side(self, point: tuple[float, float]) -> int:
        x1, y1 = self.line_start
        x2, y2 = self.line_end
        x, y = point
        value = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
        if value > 0:
            return 1
        if value < 0:
            return -1
        return 0

    def _map_direction(self, prev_side: int, new_side: int) -> str | None:
        transition = "A_TO_B" if prev_side < new_side else "B_TO_A"
        if self.direction == "outside_to_inside":
            return "IN" if transition == "A_TO_B" else "OUT"
        if self.direction == "inside_to_outside":
            return "OUT" if transition == "A_TO_B" else "IN"
        return None

    def on_frame(self, context: dict) -> None:
        if not self.enabled:
            return

        tracks = context.get("tracks", [])
        ts = context.get("ts")
        base_ts = context.get("base_ts")
        if ts is None:
            return

        for track in tracks:
            track_id = track.get("track_id")
            bbox = track.get("bbox")
            if not track_id or not bbox or len(bbox) != 4:
                continue

            cx = (bbox[0] + bbox[2]) / 2.0
            cy = (bbox[1] + bbox[3]) / 2.0
            side = self._side((cx, cy))

            prev_side = self.track_side.get(track_id)
            if prev_side is None:
                self.track_side[track_id] = side
                continue

            if side == 0 or prev_side == 0 or side == prev_side:
                self.track_side[track_id] = side
                continue

            last_cross = self.last_cross_ts.get(track_id)
            if last_cross is not None and ts - last_cross < self.min_interval_s:
                self.track_side[track_id] = side
                continue

            direction = self._map_direction(prev_side, side)
            if direction:
                event_ts = (
                    base_ts + timedelta(seconds=float(ts)) if base_ts else datetime.now(timezone.utc)
                )
                context["result"].events.append(
                    {
                        "ts": event_ts,
                        "direction": direction,
                        "track_id": track_id,
                        "confidence": track.get("confidence"),
                    }
                )
                self.last_cross_ts[track_id] = float(ts)

            self.track_side[track_id] = side

    def on_finish(self, context: dict) -> None:
        pass
