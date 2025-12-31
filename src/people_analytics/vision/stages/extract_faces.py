from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    cv2 = None

try:
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    YOLO = None


@dataclass
class FaceCaptureConfig:
    enabled: bool = False
    model: str = "yolov8n-face.pt"
    conf: float = 0.85
    min_width: int = 80
    min_interval_s: float = 2.0
    save_on_crossing: bool = True
    crop_roi: bool = False
    padding: float = 0.2
    min_overlap: float = 0.3
    max_faces_per_frame: int = 5
    class_id: int = 0
    haar_min_neighbors: int = 3
    haar_scale_factor: float = 1.1
    dnn_prototxt: str = "models/deploy.prototxt"
    dnn_model: str = "models/res10_300x300_ssd_iter_140000_fp16.caffemodel"
    dnn_conf: float = 0.5
    output_root: str | None = None


class ExtractFacesStage:
    def __init__(self, camera_cfg: dict, faces_root: str | None = None):
        self.camera_cfg = camera_cfg
        self.faces_root = Path(faces_root) if faces_root else None
        self.model = None
        self.disabled_reason: str | None = None
        self.cfg = FaceCaptureConfig()
        self.last_saved_by_track: dict[str, float] = {}
        self.detector = "yolo"
        self.haar_detectors: list = []
        self.dnn_net = None

    def setup(self, context: dict) -> None:
        context["result"].face_captures = []
        self.last_saved_by_track = {}

        face_cfg = self.camera_cfg.get("face_capture", {})
        self.cfg.enabled = bool(face_cfg.get("enabled", False))
        self.cfg.model = str(face_cfg.get("model", self.cfg.model))
        self.cfg.conf = float(face_cfg.get("conf", self.cfg.conf))
        self.cfg.min_width = int(face_cfg.get("min_width", self.cfg.min_width))
        self.cfg.min_interval_s = float(face_cfg.get("min_interval_s", self.cfg.min_interval_s))
        self.cfg.save_on_crossing = bool(face_cfg.get("save_on_crossing", self.cfg.save_on_crossing))
        self.cfg.crop_roi = bool(face_cfg.get("crop_roi", self.cfg.crop_roi))
        self.cfg.padding = float(face_cfg.get("padding", self.cfg.padding))
        self.cfg.min_overlap = float(face_cfg.get("min_overlap", self.cfg.min_overlap))
        self.cfg.max_faces_per_frame = int(face_cfg.get("max_faces_per_frame", self.cfg.max_faces_per_frame))
        self.cfg.class_id = int(face_cfg.get("class_id", self.cfg.class_id))
        self.cfg.haar_min_neighbors = int(face_cfg.get("haar_min_neighbors", self.cfg.haar_min_neighbors))
        self.cfg.haar_scale_factor = float(face_cfg.get("haar_scale_factor", self.cfg.haar_scale_factor))
        self.cfg.dnn_prototxt = str(face_cfg.get("dnn_prototxt", self.cfg.dnn_prototxt))
        self.cfg.dnn_model = str(face_cfg.get("dnn_model", self.cfg.dnn_model))
        self.cfg.dnn_conf = float(face_cfg.get("dnn_conf", self.cfg.dnn_conf))
        self.cfg.output_root = face_cfg.get("output_root")

        if not self.cfg.enabled:
            return

        if cv2 is None:
            self.disabled_reason = "opencv-not-installed"
            context["result"].errors.append(self.disabled_reason)
            return

        if YOLO is None:
            self.disabled_reason = "ultralytics-not-installed"
            context["result"].errors.append(self.disabled_reason)
            return

        if self.cfg.output_root:
            self.faces_root = Path(self.cfg.output_root)

        if self.faces_root is None:
            self.disabled_reason = "faces-root-missing"
            context["result"].errors.append(self.disabled_reason)
            return

        if self.model is None and YOLO is not None:
            try:
                self.model = YOLO(self.cfg.model)
                self.detector = "yolo"
            except Exception as exc:
                self.disabled_reason = f"face-model-load-failed:{exc}"
                context["result"].errors.append("face-model-load-failed")

        if self.model is None and cv2 is not None:
            self.dnn_net = self._load_dnn_detector()
            if self.dnn_net is not None:
                self.detector = "dnn"
                context["result"].errors.append("face-detector-fallback-dnn")
                self.disabled_reason = None

        if self.model is None and cv2 is not None and self.dnn_net is None:
            self.haar_detectors = self._load_haar_detectors()
            if self.haar_detectors:
                self.detector = "haar"
                context["result"].errors.append("face-detector-fallback-haar")
                self.disabled_reason = None

        if self.model is None and not self.haar_detectors:
            if not self.disabled_reason:
                self.disabled_reason = "face-detector-unavailable"
                context["result"].errors.append(self.disabled_reason)

    def _resize_frame(self, frame):
        resize_cfg = self.camera_cfg.get("resize")
        if not resize_cfg or cv2 is None:
            return frame
        w = int(resize_cfg.get("w", frame.shape[1]))
        h = int(resize_cfg.get("h", frame.shape[0]))
        return cv2.resize(frame, (w, h))

    def _load_haar_detectors(self):
        if cv2 is None or not hasattr(cv2, "data"):
            return []
        candidates = [
            "haarcascade_frontalface_default.xml",
            "haarcascade_profileface.xml",
        ]
        detectors = []
        for name in candidates:
            path = str(Path(cv2.data.haarcascades) / name)
            cascade = cv2.CascadeClassifier(path)
            if not cascade.empty():
                detectors.append(cascade)
        return detectors

    def _load_dnn_detector(self):
        if cv2 is None:
            return None
        proto = Path(self.cfg.dnn_prototxt)
        model = Path(self.cfg.dnn_model)
        if not proto.exists() or not model.exists():
            return None
        try:
            return cv2.dnn.readNetFromCaffe(str(proto), str(model))
        except Exception:
            return None

    def _crop_to_roi(self, frame, roi: dict):
        x0 = int(roi.get("x", 0))
        y0 = int(roi.get("y", 0))
        w = int(roi.get("w", frame.shape[1] - x0))
        h = int(roi.get("h", frame.shape[0] - y0))
        x1 = max(0, x0)
        y1 = max(0, y0)
        x2 = min(frame.shape[1], x1 + max(1, w))
        y2 = min(frame.shape[0], y1 + max(1, h))
        return frame[y1:y2, x1:x2], (x1, y1)

    def _expand_bbox(self, bbox, padding: float, frame_shape):
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        pad_w = w * padding
        pad_h = h * padding
        nx1 = max(0, int(x1 - pad_w))
        ny1 = max(0, int(y1 - pad_h))
        nx2 = min(frame_shape[1], int(x2 + pad_w))
        ny2 = min(frame_shape[0], int(y2 + pad_h))
        if nx2 <= nx1 or ny2 <= ny1:
            return None
        return (nx1, ny1, nx2, ny2)

    def _intersection_area(self, a, b) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        return float(ix2 - ix1) * float(iy2 - iy1)

    def _match_face_to_track(self, face_bbox, tracks, eligible_track_ids: set[str]) -> tuple[str | None, float]:
        fx1, fy1, fx2, fy2 = face_bbox
        fcx = (fx1 + fx2) / 2.0
        fcy = (fy1 + fy2) / 2.0
        face_area = max(1.0, float((fx2 - fx1) * (fy2 - fy1)))

        best_track_id = None
        best_overlap = 0.0
        for track in tracks:
            track_id = track.get("track_id")
            if not track_id or track_id not in eligible_track_ids:
                continue
            bbox = track.get("bbox")
            if not bbox or len(bbox) != 4:
                continue
            if not (bbox[0] <= fcx <= bbox[2] and bbox[1] <= fcy <= bbox[3]):
                continue
            overlap = self._intersection_area(face_bbox, bbox) / face_area
            if overlap > best_overlap:
                best_overlap = overlap
                best_track_id = track_id
        return best_track_id, best_overlap

    def _format_ts(self, event_ts: datetime) -> str:
        ms = int(event_ts.microsecond / 1000)
        base = event_ts.strftime("%Y-%m-%dT%H-%M-%S")
        tz = event_ts.strftime("%z")
        if tz:
            return f"{base}-{ms:03d}{tz}"
        return f"{base}-{ms:03d}"

    def on_frame(self, context: dict) -> None:
        if self.disabled_reason or not self.cfg.enabled or self.model is None:
            return

        tracks = context.get("tracks", [])
        if not tracks:
            return

        ts = context.get("ts")
        if ts is None:
            return

        crossed_tracks = context.get("crossed_tracks", [])
        crossed_track_ids = {c.get("track_id") for c in crossed_tracks if c.get("track_id")}
        eligible_track_ids: set[str] = set()

        if self.cfg.save_on_crossing:
            eligible_track_ids.update(crossed_track_ids)

        for track in tracks:
            track_id = track.get("track_id")
            if not track_id:
                continue
            last_saved = self.last_saved_by_track.get(track_id)
            if last_saved is None or (self.cfg.min_interval_s <= 0) or (ts - last_saved >= self.cfg.min_interval_s):
                eligible_track_ids.add(track_id)

        if not eligible_track_ids:
            return

        frame = context.get("frame")
        if frame is None:
            return

        frame_resized = self._resize_frame(frame)
        roi = self.camera_cfg.get("roi")
        offset_x = 0
        offset_y = 0
        infer_frame = frame_resized
        if self.cfg.crop_roi and roi:
            infer_frame, (offset_x, offset_y) = self._crop_to_roi(frame_resized, roi)

        detections = []
        if self.detector == "yolo" and self.model is not None:
            results = self.model.predict(
                infer_frame,
                conf=self.cfg.conf,
                classes=[self.cfg.class_id],
                verbose=False,
            )
            if not results:
                return

            boxes = results[0].boxes
            if boxes is None or len(boxes) == 0:
                return

            xyxy = boxes.xyxy.cpu().numpy()
            conf = boxes.conf.cpu().numpy()
            for i in range(len(xyxy)):
                detections.append(
                    {
                        "bbox": xyxy[i].tolist(),
                        "score": float(conf[i]),
                    }
                )
        elif self.detector == "dnn" and self.dnn_net is not None:
            h, w = infer_frame.shape[:2]
            blob = cv2.dnn.blobFromImage(
                infer_frame,
                1.0,
                (300, 300),
                (104.0, 117.0, 123.0),
                False,
                False,
            )
            self.dnn_net.setInput(blob)
            output = self.dnn_net.forward()
            for i in range(output.shape[2]):
                score = float(output[0, 0, i, 2])
                if score < self.cfg.dnn_conf:
                    continue
                box = output[0, 0, i, 3:7] * [w, h, w, h]
                x1, y1, x2, y2 = [float(v) for v in box]
                detections.append(
                    {
                        "bbox": [x1, y1, x2, y2],
                        "score": score,
                    }
                )
        elif self.detector == "haar" and self.haar_detectors:
            gray = cv2.cvtColor(infer_frame, cv2.COLOR_BGR2GRAY)
            min_size = (self.cfg.min_width, self.cfg.min_width)
            for detector in self.haar_detectors:
                faces = detector.detectMultiScale(
                    gray,
                    scaleFactor=self.cfg.haar_scale_factor,
                    minNeighbors=self.cfg.haar_min_neighbors,
                    minSize=min_size,
                )
                for (x, y, w, h) in faces:
                    detections.append(
                        {
                            "bbox": [float(x), float(y), float(x + w), float(y + h)],
                            "score": 1.0,
                        }
                    )
        else:
            return

        if not detections:
            return

        segment_info = context.get("segment_info")
        if segment_info:
            store_code = segment_info.store_code
            camera_code = segment_info.camera_code
            date_str = segment_info.date.isoformat()
            seg_start = segment_info.start_time.strftime("%H-%M-%S")
        else:
            store_code = "unknown"
            camera_code = self.camera_cfg.get("camera_code", "unknown")
            date_str = datetime.now(timezone.utc).date().isoformat()
            seg_start = "unknown"

        output_dir = self.faces_root / f"store={store_code}" / f"camera={camera_code}" / f"date={date_str}"
        output_dir.mkdir(parents=True, exist_ok=True)

        saved_this_frame: set[str] = set()
        detections.sort(key=lambda d: (d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]), reverse=True)
        face_limit = min(len(detections), self.cfg.max_faces_per_frame)
        for i in range(face_limit):
            score = float(detections[i]["score"])
            if score < self.cfg.conf:
                continue
            x1, y1, x2, y2 = detections[i]["bbox"]
            x1 += offset_x
            x2 += offset_x
            y1 += offset_y
            y2 += offset_y
            width = x2 - x1
            if width < self.cfg.min_width:
                continue

            face_bbox = [float(x1), float(y1), float(x2), float(y2)]
            track_id, overlap = self._match_face_to_track(face_bbox, tracks, eligible_track_ids)
            if not track_id or overlap < self.cfg.min_overlap:
                continue
            if track_id in saved_this_frame:
                continue

            last_saved = self.last_saved_by_track.get(track_id)
            if last_saved is not None and self.cfg.min_interval_s > 0 and ts - last_saved < self.cfg.min_interval_s:
                continue

            expanded = self._expand_bbox(face_bbox, self.cfg.padding, frame_resized.shape)
            if not expanded:
                continue
            ex1, ey1, ex2, ey2 = expanded
            face_crop = frame_resized[ey1:ey2, ex1:ex2]
            if face_crop.size == 0:
                continue

            base_ts = context.get("base_ts")
            if base_ts:
                event_ts = base_ts + timedelta(seconds=float(ts))
            else:
                event_ts = datetime.now(timezone.utc)

            ts_str = self._format_ts(event_ts)
            source = "crossing" if track_id in crossed_track_ids else "interval"
            filename = (
                f"store={store_code}__camera={camera_code}__date={date_str}__"
                f"seg={seg_start}__ts={ts_str}__track={track_id}__score={score:.2f}.jpg"
            )
            out_path = output_dir / filename
            ok = cv2.imwrite(str(out_path), face_crop)
            if not ok:
                context["result"].errors.append("face-save-failed")
                continue

            rel_path = out_path
            try:
                rel_path = out_path.relative_to(self.faces_root)
            except Exception:
                pass

            context["result"].face_captures.append(
                {
                    "ts": event_ts,
                    "track_id": track_id,
                    "store_code": store_code,
                    "camera_code": camera_code,
                    "segment_date": date_str,
                    "segment_start": seg_start,
                    "source": source,
                    "face_score": score,
                    "face_bbox": face_bbox,
                    "path": str(rel_path),
                }
            )
            self.last_saved_by_track[track_id] = float(ts)
            saved_this_frame.add(track_id)

    def on_finish(self, context: dict) -> None:
        pass
