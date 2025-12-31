from __future__ import annotations

from sqlalchemy import delete

from people_analytics.db.models.event_flow import PeopleFlowEvent
from people_analytics.db.models.metrics_presence import PresenceSample
from people_analytics.vision.pipeline import PipelineResult


def replace_events_for_segment(session, segment_id: int, store_id: int, camera_id: int, result: PipelineResult) -> None:
    session.execute(delete(PeopleFlowEvent).where(PeopleFlowEvent.segment_id == segment_id))
    session.execute(delete(PresenceSample).where(PresenceSample.segment_id == segment_id))

    for event in result.events:
        session.add(
            PeopleFlowEvent(
                store_id=store_id,
                camera_id=camera_id,
                segment_id=segment_id,
                ts=event["ts"],
                direction=event["direction"],
                is_staff=event.get("is_staff", False),
                track_id=event.get("track_id"),
                confidence=event.get("confidence"),
            )
        )

    for sample in result.presence_samples:
        session.add(
            PresenceSample(
                store_id=store_id,
                camera_id=camera_id,
                segment_id=segment_id,
                ts=sample["ts"],
                count=sample["count"],
            )
        )
