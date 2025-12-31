class CountLineStage:
    def __init__(self, camera_cfg: dict):
        self.camera_cfg = camera_cfg

    def setup(self, context: dict) -> None:
        context["result"].events = []

    def on_frame(self, context: dict) -> None:
        # Hook for line crossing logic based on tracked trajectories.
        # Add events in the form:
        # {"ts": <datetime>, "direction": "IN"|"OUT", "track_id": "..."}
        pass

    def on_finish(self, context: dict) -> None:
        pass
