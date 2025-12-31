class StaffExclusionStage:
    def __init__(self, camera_cfg: dict):
        self.camera_cfg = camera_cfg

    def setup(self, context: dict) -> None:
        pass

    def on_frame(self, context: dict) -> None:
        # Hook for staff matching on IN events only.
        pass

    def on_finish(self, context: dict) -> None:
        pass
