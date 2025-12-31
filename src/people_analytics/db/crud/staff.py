from __future__ import annotations

from sqlalchemy import select

from people_analytics.db.models.staff import StaffProfile


def list_staff(session, store_id: int) -> list[StaffProfile]:
    return list(session.execute(select(StaffProfile).where(StaffProfile.store_id == store_id)).scalars())
