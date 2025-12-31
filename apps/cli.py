from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

from people_analytics.core.config import (
    load_camera_config,
    load_shifts_config,
    load_stores_config,
)
from people_analytics.core.logging import configure_logging
from people_analytics.core.settings import get_settings
from people_analytics.core.timeutils import combine_date_time
from people_analytics.db.crud import events as events_crud
from people_analytics.db.crud import jobs as jobs_crud
from people_analytics.db.crud import segments as segments_crud
from people_analytics.db.session import get_session, init_db
from people_analytics.kpi.rebuild import rebuild_for_date
from people_analytics.storage.scanner import scan_videos
from people_analytics.storage.paths import parse_video_path
from people_analytics.vision.pipeline import build_pipeline

app = typer.Typer(help="People analytics CLI")


@app.command(name="init-db")
def init_db_cmd() -> None:
    configure_logging()
    init_db()
    rprint("[green]DB initialized[/green]")


@app.command()
def ingest(
    video_root: Optional[str] = None,
    dry_run: bool = False,
    limit: int = 0,
) -> None:
    configure_logging()
    settings = get_settings()
    root = Path(video_root or settings.video_root)
    store_cfg = load_stores_config(settings.config_dir)

    count = 0
    with get_session() as session:
        for info in scan_videos(root):
            store = segments_crud.ensure_store(session, info.store_code, store_cfg.get(info.store_code))
            camera = segments_crud.ensure_camera(session, store.id, info.camera_code)
            segment, created = segments_crud.upsert_video_segment(session, store.id, camera.id, info, root)
            if created and not dry_run:
                jobs_crud.enqueue_job(session, "PROCESS_SEGMENT", {"segment_id": segment.id})
            count += 1
            if limit and count >= limit:
                break
    rprint(f"[green]Ingest scanned {count} files[/green]")


@app.command()
def process(
    segment_id: Optional[int] = None,
    path: Optional[str] = None,
    print_json: bool = True,
) -> None:
    configure_logging()
    settings = get_settings()

    if not segment_id and not path:
        raise typer.BadParameter("Provide --segment-id or --path")

    if path:
        video_path = Path(path)
        info = parse_video_path(video_path, Path(settings.video_root))
        camera_cfg = load_camera_config(settings.config_dir, info.store_code, info.camera_code)
        pipeline = build_pipeline(camera_cfg)
        base_ts = combine_date_time(info.date, info.start_time, settings.timezone)
        result = pipeline.run(video_path, base_ts=base_ts)
        output = result.to_output(info, settings.timezone)
    else:
        with get_session() as session:
            segment = segments_crud.get_segment(session, segment_id)
            if not segment:
                raise typer.BadParameter(f"Segment not found: {segment_id}")
            store = segments_crud.get_store(session, segment.store_id)
            camera = segments_crud.get_camera(session, segment.camera_id)
            camera_cfg = load_camera_config(settings.config_dir, store.code, camera.camera_code)
            pipeline = build_pipeline(camera_cfg)
            video_path = Path(settings.video_root) / segment.path
            result = pipeline.run(video_path, base_ts=segment.start_time)
            events_crud.replace_events_for_segment(session, segment.id, store.id, camera.id, result)
            output = result.to_output(
                segment.to_path_info(store.code, camera.camera_code, settings.timezone),
                settings.timezone,
            )

    if print_json:
        print(json.dumps(output, default=str))


@app.command(name="kpi-rebuild")
def kpi_rebuild(
    date: str,
    store_id: int,
    camera_id: Optional[int] = None,
) -> None:
    configure_logging()
    settings = get_settings()
    shifts_cfg = load_shifts_config(settings.config_dir)
    with get_session() as session:
        rebuild_for_date(session, store_id, camera_id, date, shifts_cfg, settings.timezone)
    rprint("[green]KPI rebuild done[/green]")


@app.command(name="staff-rebuild")
def staff_rebuild(store_code: str) -> None:
    configure_logging()
    rprint(f"[yellow]Staff rebuild stub for store {store_code}[/yellow]")


if __name__ == "__main__":
    app()
