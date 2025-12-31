from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_, select

from people_analytics.db.models.job import Job


def enqueue_job(session, job_type: str, payload: dict, run_after: datetime | None = None) -> Job:
    if run_after is None:
        run_after = datetime.now(timezone.utc)
    job = Job(
        type=job_type,
        payload_json=payload,
        status="queued",
        run_after=run_after,
    )
    session.add(job)
    session.flush()
    return job


def claim_job(session, worker_id: str) -> Job | None:
    now = datetime.now(timezone.utc)
    stmt = (
        select(Job)
        .where(Job.status == "queued", or_(Job.run_after.is_(None), Job.run_after <= now))
        .order_by(Job.run_after, Job.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = session.execute(stmt).scalars().first()
    if not job:
        return None
    job.status = "processing"
    job.locked_at = now
    job.locked_by = worker_id
    job.attempts = (job.attempts or 0) + 1
    session.flush()
    return job


def mark_done(session, job: Job) -> None:
    job.status = "done"
    session.flush()


def mark_failed(session, job: Job, error: str) -> None:
    job.status = "failed"
    job.last_error = error
    session.flush()
