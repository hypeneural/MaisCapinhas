from pathlib import Path

from people_analytics.storage.paths import parse_video_path


def test_parse_video_path():
    root = Path("/var/people_analytics/videos")
    path = root / "store=001/camera=entrance/date=2025-12-31/14-00-00__14-10-00.mp4"
    info = parse_video_path(path, root)
    assert info.store_code == "001"
    assert info.camera_code == "entrance"
    assert info.date.isoformat() == "2025-12-31"
    assert info.start_time.isoformat() == "14:00:00"
    assert info.end_time.isoformat() == "14:10:00"
    assert info.relative_path.endswith("14-00-00__14-10-00.mp4")
