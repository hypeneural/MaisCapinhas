class TrackPeopleStage:
    def __init__(self, camera_cfg: dict):
        self.camera_cfg = camera_cfg

    def setup(self, context: dict) -> None:
        context["tracks"] = []

    def on_frame(self, context: dict) -> None:
        # Hook for tracker (ByteTrack / BoT-SORT)
        context["tracks"] = []

    def on_finish(self, context: dict) -> None:
        pass
