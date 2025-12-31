from __future__ import annotations

from collections import defaultdict


def aggregate_hourly(events: list[dict]) -> dict[int, dict]:
    buckets = defaultdict(lambda: {"in": 0, "out": 0, "staff_in": 0, "staff_out": 0})
    for event in events:
        ts = event["ts"]
        hour = ts.hour
        is_staff = event.get("is_staff", False)
        if event["direction"] == "IN":
            buckets[hour]["in"] += 1
            if is_staff:
                buckets[hour]["staff_in"] += 1
        elif event["direction"] == "OUT":
            buckets[hour]["out"] += 1
            if is_staff:
                buckets[hour]["staff_out"] += 1
    return buckets
