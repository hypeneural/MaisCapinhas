from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from people_analytics.core.settings import get_settings
from people_analytics.core.timeutils import combine_date_time, to_utc
from people_analytics.db.models.camera import Camera
from people_analytics.db.models.store import Store
from people_analytics.db.models.video_segment import VideoSegment
from people_analytics.storage.fingerprint import fingerprint_for_file
from people_analytics.storage.paths import VideoPathInfo


def ensure_store(session, store_code: str, store_cfg: dict | None) -> Store:
    store = session.execute(select(Store).where(Store.code == store_code)).scalar_one_or_none()
    if store:
        return store
    store = Store(
        code=store_code,
        name=(store_cfg or {}).get("name"),
        city=(store_cfg or {}).get("city"),
    )
    session.add(store)
    session.flush()
    return store


def ensure_camera(session, store_id: int, camera_code: str) -> Camera:
    camera = session.execute(
        select(Camera).where(Camera.store_id == store_id, Camera.camera_code == camera_code)
    ).scalar_one_or_none()
    if camera:
        return camera
    camera = Camera(store_id=store_id, camera_code=camera_code)
    session.add(camera)
    session.flush()
    return camera


def upsert_video_segment(
    session,
    store_id: int,
    camera_id: int,
    info: VideoPathInfo,
    video_root: Path,
) -> tuple[VideoSegment, bool]:
    existing = session.execute(
        select(VideoSegment).where(VideoSegment.path == info.relative_path)
    ).scalar_one_or_none()
    if existing:
        return existing, False

    settings = get_settings()
    start_dt_local = combine_date_time(info.date, info.start_time, settings.timezone)
    end_dt_local = combine_date_time(info.date, info.end_time, settings.timezone)
    start_dt = to_utc(start_dt_local, settings.timezone)
    end_dt = to_utc(end_dt_local, settings.timezone)

    abs_path = video_root / info.relative_path
    fingerprint = fingerprint_for_file(abs_path)
    file_size = abs_path.stat().st_size if abs_path.exists() else None

    segment = VideoSegment(
        store_id=store_id,
        camera_id=camera_id,
        path=info.relative_path,
        start_time=start_dt,
        end_time=end_dt,
        duration_seconds=int((end_dt - start_dt).total_seconds()),
        fingerprint=fingerprint,
        file_size=file_size,
    )
    session.add(segment)
    session.flush()
    return segment, True


def get_segment(session, segment_id: int) -> VideoSegment | None:
    return session.get(VideoSegment, segment_id)


def list_segments(session, limit: int) -> list[VideoSegment]:
    return list(session.execute(select(VideoSegment).order_by(VideoSegment.id.desc()).limit(limit)).scalars())


def get_store(session, store_id: int) -> Store | None:
    return session.get(Store, store_id)


def get_camera(session, camera_id: int) -> Camera | None:
    return session.get(Camera, camera_id)


def list_stores(session) -> list[Store]:
    return list(session.execute(select(Store).order_by(Store.id)).scalars())
