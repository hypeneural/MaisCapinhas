from __future__ import annotations

try:
    import numpy as np  # type: ignore
    import supervision as sv  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    np = None
    sv = None


class TrackPeopleStage:
    def __init__(self, camera_cfg: dict):
        self.camera_cfg = camera_cfg
        self.tracker = None
        self.disabled_reason: str | None = None

    def setup(self, context: dict) -> None:
        context["tracks"] = []

        if sv is None or np is None:
            self.disabled_reason = "supervision-not-installed"
            context["result"].errors.append(self.disabled_reason)
            return

        tracking_cfg = self.camera_cfg.get("tracking", {})
        processing = self.camera_cfg.get("processing", {})
        frame_rate = tracking_cfg.get("frame_rate") or processing.get("target_fps") or 30

        try:
            self.tracker = sv.ByteTrack(
                frame_rate=int(frame_rate),
                track_activation_threshold=float(tracking_cfg.get("track_thresh", 0.35)),
                minimum_matching_threshold=float(tracking_cfg.get("match_thresh", 0.8)),
                lost_track_buffer=int(tracking_cfg.get("track_buffer", 30)),
                minimum_consecutive_frames=int(tracking_cfg.get("min_consecutive_frames", 1)),
            )
        except TypeError:
            try:
                self.tracker = sv.ByteTrack(
                    frame_rate=int(frame_rate),
                    track_thresh=float(tracking_cfg.get("track_thresh", 0.35)),
                    match_thresh=float(tracking_cfg.get("match_thresh", 0.8)),
                    track_buffer=int(tracking_cfg.get("track_buffer", 30)),
                )
            except Exception as exc:
                self.disabled_reason = f"tracker-init-failed:{exc}"
                context["result"].errors.append("tracker-init-failed")
        except Exception as exc:
            self.disabled_reason = f"tracker-init-failed:{exc}"
            context["result"].errors.append("tracker-init-failed")

    def on_frame(self, context: dict) -> None:
        if self.disabled_reason or self.tracker is None or sv is None or np is None:
            context["tracks"] = []
            return

        detections = context.get("detections", [])
        if not detections:
            context["tracks"] = []
            return

        xyxy = np.array([d["bbox"] for d in detections], dtype=float)
        confidence = np.array([d["confidence"] for d in detections], dtype=float)
        class_id = np.array([d["class_id"] for d in detections], dtype=int)

        sv_detections = sv.Detections(xyxy=xyxy, confidence=confidence, class_id=class_id)
        tracked = self.tracker.update_with_detections(sv_detections)
        context["tracks"] = self._to_tracks(tracked)

    def _to_tracks(self, detections) -> list[dict]:
        if detections is None or len(detections) == 0:
            return []

        tracks = []
        tracker_ids = getattr(detections, "tracker_id", None)
        for i in range(len(detections)):
            track_id = None
            if tracker_ids is not None:
                track_id = tracker_ids[i]
            if track_id is None:
                continue
            bbox = detections.xyxy[i].tolist()
            confidence = None
            if getattr(detections, "confidence", None) is not None:
                confidence = float(detections.confidence[i])
            class_id = None
            if getattr(detections, "class_id", None) is not None:
                class_id = int(detections.class_id[i])
            tracks.append(
                {
                    "track_id": str(int(track_id)),
                    "bbox": [float(v) for v in bbox],
                    "confidence": confidence,
                    "class_id": class_id,
                }
            )
        return tracks

    def on_finish(self, context: dict) -> None:
        pass
