class DetectPeopleStage:
    def __init__(self, camera_cfg: dict):
        self.camera_cfg = camera_cfg

    def setup(self, context: dict) -> None:
        context["detections"] = []

    def on_frame(self, context: dict) -> None:
        # Hook for real detector (YOLO, etc.)
        context["detections"] = []

    def on_finish(self, context: dict) -> None:
        pass
