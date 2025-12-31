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

    def on_frame(self, context: dict) -> None:
        if self.disabled_reason or self.model is None:
            context["detections"] = []
            return

        frame = self._resize_frame(context["frame"])
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

        roi = self.camera_cfg.get("roi")
        detections = []
        for i in range(len(xyxy)):
            x1, y1, x2, y2 = xyxy[i].tolist()
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            if roi:
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
