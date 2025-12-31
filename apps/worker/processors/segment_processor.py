from __future__ import annotations

from pathlib import Path

from people_analytics.core.config import load_camera_config
from people_analytics.core.settings import get_settings
from people_analytics.core.timeutils import to_local
from people_analytics.db.crud import events as events_crud
from people_analytics.db.crud import jobs as jobs_crud
from people_analytics.db.crud import segments as segments_crud
from people_analytics.db.models.job import Job
from people_analytics.vision.pipeline import build_pipeline


def process_segment_job(session, job: Job) -> None:
    payload = job.payload_json or {}
    segment_id = payload.get("segment_id")
    if not segment_id:
        raise ValueError("Missing segment_id in payload")

    settings = get_settings()
    segment = segments_crud.get_segment(session, segment_id)
    if not segment:
        raise ValueError(f"Segment not found: {segment_id}")

    store = segments_crud.get_store(session, segment.store_id)
    camera = segments_crud.get_camera(session, segment.camera_id)

    camera_cfg = load_camera_config(settings.config_dir, store.code, camera.camera_code)
    pipeline = build_pipeline(camera_cfg)

    video_path = Path(settings.video_root) / segment.path
    result = pipeline.run(video_path)

    events_crud.replace_events_for_segment(session, segment.id, store.id, camera.id, result)

    local_date = to_local(segment.start_time, settings.timezone).date()
    jobs_crud.enqueue_job(
        session,
        "KPI_REBUILD",
        {
            "store_id": store.id,
            "camera_id": camera.id,
            "date": local_date.isoformat(),
        },
    )
