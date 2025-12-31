from fastapi import APIRouter

from people_analytics.db.crud import kpis as kpis_crud
from people_analytics.db.session import get_session

router = APIRouter()


@router.get("/hourly")
def hourly_kpis(store_id: int, date: str, camera_id: int | None = None) -> list[dict]:
    with get_session() as session:
        rows = kpis_crud.list_hourly(session, store_id, camera_id, date)
        return [r.to_dict() for r in rows]


@router.get("/shift")
def shift_kpis(store_id: int, date: str, camera_id: int | None = None) -> list[dict]:
    with get_session() as session:
        rows = kpis_crud.list_shift(session, store_id, camera_id, date)
        return [r.to_dict() for r in rows]
