from __future__ import annotations

import time

from people_analytics.core.config import load_shifts_config
from people_analytics.core.logging import configure_logging
from people_analytics.core.settings import get_settings
from people_analytics.db.crud import jobs as jobs_crud
from people_analytics.db.session import get_session
from apps.worker.processors.segment_processor import process_segment_job
from people_analytics.kpi.rebuild import rebuild_for_date


def run_worker() -> None:
    configure_logging()
    settings = get_settings()
    poll = settings.job_poll_interval
    shifts_cfg = load_shifts_config(settings.config_dir)

    while True:
        with get_session() as session:
            job = jobs_crud.claim_job(session, settings.worker_id)
            if not job:
                time.sleep(poll)
                continue

            try:
                if job.type == "PROCESS_SEGMENT":
                    process_segment_job(session, job)
                elif job.type == "KPI_REBUILD":
                    payload = job.payload_json or {}
                    rebuild_for_date(
                        session,
                        payload.get("store_id"),
                        payload.get("camera_id"),
                        payload.get("date"),
                        shifts_cfg,
                        settings.timezone,
                    )
                else:
                    raise ValueError(f"Unknown job type: {job.type}")
                jobs_crud.mark_done(session, job)
            except Exception as exc:
                jobs_crud.mark_failed(session, job, str(exc))

        time.sleep(0.1)


if __name__ == "__main__":
    run_worker()
