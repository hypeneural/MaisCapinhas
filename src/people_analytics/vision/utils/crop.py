from __future__ import annotations


def crop(frame, roi: dict):
    x = roi.get("x", 0)
    y = roi.get("y", 0)
    w = roi.get("w", 0)
    h = roi.get("h", 0)
    return frame[y : y + h, x : x + w]
