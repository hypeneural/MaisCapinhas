from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update

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


def _requeue_stale_jobs(session, now: datetime, lock_timeout_s: int) -> None:
    if lock_timeout_s <= 0:
        return
    stale_before = now - timedelta(seconds=lock_timeout_s)
    session.execute(
        update(Job)
        .where(
            Job.status == "processing",
            Job.locked_at.is_not(None),
            Job.locked_at < stale_before,
            Job.attempts < Job.max_attempts,
        )
        .values(status="queued", locked_at=None, locked_by=None, last_error="stale-lock-requeued")
    )
    session.execute(
        update(Job)
        .where(
            Job.status == "processing",
            Job.locked_at.is_not(None),
            Job.locked_at < stale_before,
            Job.attempts >= Job.max_attempts,
        )
        .values(status="failed", last_error="max-attempts-exceeded")
    )


def claim_job(session, worker_id: str, lock_timeout_s: int | None = None) -> Job | None:
    now = datetime.now(timezone.utc)
    if lock_timeout_s is not None:
        _requeue_stale_jobs(session, now, lock_timeout_s)
    stmt = (
        select(Job)
        .where(
            Job.status == "queued",
            Job.attempts < Job.max_attempts,
            or_(Job.run_after.is_(None), Job.run_after <= now),
        )
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
