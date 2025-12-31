from __future__ import annotations

from datetime import datetime, timedelta, time

from sqlalchemy import select

from people_analytics.core.timeutils import parse_date, to_local
from people_analytics.db.crud import kpis as kpis_crud
from people_analytics.db.models.event_flow import PeopleFlowEvent
from people_analytics.kpi.aggregators.hourly import aggregate_hourly
from people_analytics.kpi.aggregators.shift import aggregate_shift


def rebuild_for_date(session, store_id: int, camera_id: int | None, day: str, shifts_cfg: dict | None, tz_name: str) -> None:
    if store_id is None:
        raise ValueError("store_id required")

    day_date = parse_date(day)
    start = datetime.combine(day_date, time.min)
    end = start + timedelta(days=1)
    stmt = select(PeopleFlowEvent).where(
        PeopleFlowEvent.store_id == store_id,
        PeopleFlowEvent.ts >= start,
        PeopleFlowEvent.ts < end,
    )
    if camera_id is not None:
        stmt = stmt.where(PeopleFlowEvent.camera_id == camera_id)

    events = []
    for row in session.execute(stmt).scalars():
        events.append(
            {
                "ts": to_local(row.ts, tz_name),
                "direction": row.direction,
                "is_staff": row.is_staff,
            }
        )

    hourly = aggregate_hourly(events)
    hourly_rows = [
        {
            "hour": hour,
            "in_count": counts["in"],
            "out_count": counts["out"],
            "staff_in": counts["staff_in"],
            "staff_out": counts["staff_out"],
        }
        for hour, counts in hourly.items()
    ]
    kpis_crud.replace_hourly(session, store_id, camera_id, day_date, hourly_rows)

    if shifts_cfg and shifts_cfg.get("shifts"):
        shift_counts = aggregate_shift(events, shifts_cfg.get("shifts"))
        shift_rows = [
            {
                "shift_id": shift_id,
                "in_count": counts["in"],
                "out_count": counts["out"],
                "staff_in": counts["staff_in"],
                "staff_out": counts["staff_out"],
            }
            for shift_id, counts in shift_counts.items()
        ]
        kpis_crud.replace_shift(session, store_id, camera_id, day_date, shift_rows)
