from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select

from people_analytics.db.models.kpi_hourly import KpiHourly
from people_analytics.db.models.kpi_shift import KpiShift
from people_analytics.core.timeutils import parse_date


def replace_hourly(session, store_id: int, camera_id: int | None, day: date, rows: list[dict]) -> None:
    session.execute(
        delete(KpiHourly).where(
            KpiHourly.store_id == store_id,
            KpiHourly.camera_id == camera_id,
            KpiHourly.date == day,
        )
    )
    for row in rows:
        session.add(KpiHourly(store_id=store_id, camera_id=camera_id, date=day, **row))


def replace_shift(session, store_id: int, camera_id: int | None, day: date, rows: list[dict]) -> None:
    session.execute(
        delete(KpiShift).where(
            KpiShift.store_id == store_id,
            KpiShift.camera_id == camera_id,
            KpiShift.date == day,
        )
    )
    for row in rows:
        session.add(KpiShift(store_id=store_id, camera_id=camera_id, date=day, **row))


def list_hourly(session, store_id: int, camera_id: int | None, day: str) -> list[KpiHourly]:
    day_date = parse_date(day)
    stmt = select(KpiHourly).where(KpiHourly.store_id == store_id, KpiHourly.date == day_date)
    if camera_id is not None:
        stmt = stmt.where(KpiHourly.camera_id == camera_id)
    return list(session.execute(stmt).scalars())


def list_shift(session, store_id: int, camera_id: int | None, day: str) -> list[KpiShift]:
    day_date = parse_date(day)
    stmt = select(KpiShift).where(KpiShift.store_id == store_id, KpiShift.date == day_date)
    if camera_id is not None:
        stmt = stmt.where(KpiShift.camera_id == camera_id)
    return list(session.execute(stmt).scalars())
