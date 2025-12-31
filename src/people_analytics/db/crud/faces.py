from __future__ import annotations

from sqlalchemy import delete

from people_analytics.db.models.face_capture import FaceCapture
from people_analytics.vision.pipeline import PipelineResult


def replace_faces_for_segment(session, segment_id: int, store_id: int, camera_id: int, result: PipelineResult) -> None:
    session.execute(delete(FaceCapture).where(FaceCapture.segment_id == segment_id))

    for face in result.face_captures:
        session.add(
            FaceCapture(
                store_id=store_id,
                camera_id=camera_id,
                segment_id=segment_id,
                ts=face["ts"],
                track_id=face.get("track_id"),
                source=face.get("source"),
                face_score=face.get("face_score"),
                face_bbox=face.get("face_bbox"),
                path=face.get("path"),
            )
        )
