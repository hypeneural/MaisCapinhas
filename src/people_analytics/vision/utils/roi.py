from __future__ import annotations


def point_in_roi(point: tuple[int, int], roi: dict) -> bool:
    x, y = point
    return (
        x >= roi.get("x", 0)
        and y >= roi.get("y", 0)
        and x <= roi.get("x", 0) + roi.get("w", 0)
        and y <= roi.get("y", 0) + roi.get("h", 0)
    )
