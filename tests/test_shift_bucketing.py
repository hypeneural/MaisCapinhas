from datetime import datetime
from zoneinfo import ZoneInfo

from people_analytics.kpi.aggregators.shift import get_shift_id


def test_shift_bucket():
    shifts = [
        {"id": "MORNING", "start": "08:00", "end": "12:00"},
        {"id": "AFTERNOON", "start": "12:00", "end": "18:00"},
    ]
    ts = datetime(2025, 1, 1, 9, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert get_shift_id(ts, shifts) == "MORNING"
