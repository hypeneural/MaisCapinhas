class ReIdEmbeddingsStage:
    def __init__(self, camera_cfg: dict):
        self.camera_cfg = camera_cfg

    def setup(self, context: dict) -> None:
        pass

    def on_frame(self, context: dict) -> None:
        # Future stage for re-identification embeddings.
        pass

    def on_finish(self, context: dict) -> None:
        pass
