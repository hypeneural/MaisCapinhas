from __future__ import annotations

from datetime import datetime, time


def _parse_time(value: str) -> time:
    return time.fromisoformat(value)


def get_shift_id(ts_local: datetime, shifts: list[dict]) -> str | None:
    for shift in shifts:
        start = _parse_time(shift["start"])
        end = _parse_time(shift["end"])
        if start <= ts_local.time() < end:
            return shift["id"]
    return None


def aggregate_shift(events: list[dict], shifts: list[dict]) -> dict[str, dict]:
    buckets: dict[str, dict] = {}
    for event in events:
        shift_id = get_shift_id(event["ts"], shifts)
        if not shift_id:
            continue
        if shift_id not in buckets:
            buckets[shift_id] = {"in": 0, "out": 0, "staff_in": 0, "staff_out": 0}
        is_staff = event.get("is_staff", False)
        if event["direction"] == "IN":
            buckets[shift_id]["in"] += 1
            if is_staff:
                buckets[shift_id]["staff_in"] += 1
        elif event["direction"] == "OUT":
            buckets[shift_id]["out"] += 1
            if is_staff:
                buckets[shift_id]["staff_out"] += 1
    return buckets
