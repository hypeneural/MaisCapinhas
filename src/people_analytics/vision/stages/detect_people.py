from __future__ import annotations

from typing import Any

try:
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    YOLO = None

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    cv2 = None


class DetectPeopleStage:
    def __init__(self, camera_cfg: dict):
        self.camera_cfg = camera_cfg
        self.model = None
        self.disabled_reason: str | None = None
        self.conf = 0.35
        self.iou = 0.45
        self.person_class_id = 0
        self.crop_roi = False

    def setup(self, context: dict) -> None:
        context["detections"] = []

        if YOLO is None:
            self.disabled_reason = "ultralytics-not-installed"
            context["result"].errors.append(self.disabled_reason)
            return

        processing = self.camera_cfg.get("processing", {})
        model_path = processing.get("yolo_model", "yolov8n.pt")
        self.conf = float(processing.get("conf", 0.35))
        self.iou = float(processing.get("iou", 0.45))
        self.person_class_id = int(processing.get("person_class_id", 0))
        self.crop_roi = bool(processing.get("crop_roi", False))

        if self.model is None:
            try:
                self.model = YOLO(model_path)
            except Exception as exc:
                self.disabled_reason = f"yolo-load-failed:{exc}"
                context["result"].errors.append("yolo-load-failed")

    def _resize_frame(self, frame) -> Any:
        resize_cfg = self.camera_cfg.get("resize")
        if not resize_cfg:
            return frame
        if cv2 is None:
            if not self.disabled_reason:
                self.disabled_reason = "opencv-not-installed"
            return frame
        w = int(resize_cfg.get("w", frame.shape[1]))
        h = int(resize_cfg.get("h", frame.shape[0]))
        return cv2.resize(frame, (w, h))

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

    def on_frame(self, context: dict) -> None:
        if self.disabled_reason or self.model is None:
            context["detections"] = []
            return

        frame = self._resize_frame(context["frame"])
        roi = self.camera_cfg.get("roi")
        offset_x = 0
        offset_y = 0
        if self.crop_roi and roi:
            frame, (offset_x, offset_y) = self._crop_to_roi(frame, roi)
        results = self.model.predict(
            frame,
            conf=self.conf,
            iou=self.iou,
            classes=[self.person_class_id],
            verbose=False,
        )
        if not results:
            context["detections"] = []
            return

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            context["detections"] = []
            return

        xyxy = boxes.xyxy.cpu().numpy()
        conf = boxes.conf.cpu().numpy()
        cls = boxes.cls.cpu().numpy().astype(int)

        detections = []
        for i in range(len(xyxy)):
            x1, y1, x2, y2 = xyxy[i].tolist()
            x1 += offset_x
            x2 += offset_x
            y1 += offset_y
            y2 += offset_y
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            if roi and not self.crop_roi:
                x0 = roi.get("x", 0)
                y0 = roi.get("y", 0)
                w = roi.get("w", 0)
                h = roi.get("h", 0)
                if not (x0 <= cx <= x0 + w and y0 <= cy <= y0 + h):
                    continue
            detections.append(
                {
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                    "confidence": float(conf[i]),
                    "class_id": int(cls[i]),
                }
            )

        context["detections"] = detections

    def on_finish(self, context: dict) -> None:
        pass
