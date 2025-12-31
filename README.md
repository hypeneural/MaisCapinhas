# People Analytics

Modular offline pipeline to ingest security videos by store/camera/date, queue jobs in the database, and compute KPIs. The design favors a simple DB-backed job queue and a stage-based vision pipeline so new KPIs can be added without reworking the core flow.

## Video folder structure (required)

Do not depend on filename. Depend on folder structure.

```
/var/people_analytics/videos/
  store=001/
    camera=entrance/
      date=2025-12-31/
        14-00-00__14-10-00.mp4
        14-10-00__14-20-00.mp4
```

## Quickstart

1) Create and activate a venv
2) Install dependencies
3) Copy `.env.example` to `.env` and adjust paths
4) Initialize DB
5) Ingest videos
6) Run worker
7) Start API

Example:

```
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
copy .env.example .env
python -m apps.cli init-db
python -m apps.cli ingest
python -m apps.worker.worker
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Notes

- Postgres is recommended for `SELECT ... FOR UPDATE SKIP LOCKED` when running multiple workers.
- SQLite is fine for single-worker dev, but has limited locking behavior.
- `python -m apps.cli process --path <file>` prints JSON output after reading a video.

## Output JSON example

```
{
  "segment": {
    "store_code": "001",
    "camera_code": "entrance",
    "start_time": "2025-12-31T14:00:00-03:00",
    "end_time": "2025-12-31T14:10:00-03:00"
  },
  "counts": {
    "in": 0,
    "out": 0,
    "staff_in": 0,
    "staff_out": 0
  },
  "events": [],
  "presence_samples": [],
  "meta": {
    "frames_read": 0,
    "duration_s": null,
    "errors": ["opencv-not-installed"]
  }
}
```
