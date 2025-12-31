from fastapi import APIRouter

from people_analytics.db.crud import segments as segments_crud
from people_analytics.db.session import get_session

router = APIRouter()


@router.get("")
def list_segments(limit: int = 100) -> list[dict]:
    with get_session() as session:
        segments = segments_crud.list_segments(session, limit)
        return [s.to_dict() for s in segments]
