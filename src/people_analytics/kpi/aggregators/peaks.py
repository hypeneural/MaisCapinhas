from __future__ import annotations

from datetime import timedelta


def peak_window(events: list[dict], window_minutes: int = 60) -> dict | None:
    if not events:
        return None
    events = sorted(events, key=lambda e: e["ts"])
    best = None
    window = timedelta(minutes=window_minutes)

    for event in events:
        start = event["ts"]
        end = start + window
        count = sum(1 for e in events if start <= e["ts"] < end and e["direction"] == "IN")
        if not best or count > best["count"]:
            best = {"start": start, "end": end, "count": count}
    return best
