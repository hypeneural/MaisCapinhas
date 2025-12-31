from __future__ import annotations


def compute_occupancy(events: list[dict]) -> dict:
    current = 0
    max_occ = 0
    for event in sorted(events, key=lambda e: e["ts"]):
        if event["direction"] == "IN":
            current += 1
        elif event["direction"] == "OUT":
            current = max(0, current - 1)
        max_occ = max(max_occ, current)
    return {"max": max_occ}
