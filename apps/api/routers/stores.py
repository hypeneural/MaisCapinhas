from fastapi import APIRouter

from people_analytics.db.crud import segments as segments_crud
from people_analytics.db.session import get_session

router = APIRouter()


@router.get("")
def list_stores() -> list[dict]:
    with get_session() as session:
        stores = segments_crud.list_stores(session)
        return [s.to_dict() for s in stores]
