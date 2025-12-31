from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, time, timezone
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


def _split_with_ffmpeg(
    input_path: Path,
    output_dir: Path,
    segment_seconds: int,
    fps: int,
    scale: str,
    crf: int,
    preset: str,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "seg_%03d.mp4"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        f"scale={scale},fps={fps}",
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-an",
        "-f",
        "segment",
        "-segment_time",
        str(segment_seconds),
        "-reset_timestamps",
        "1",
        str(pattern),
    ]
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise typer.BadParameter("ffmpeg not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise typer.BadParameter(f"ffmpeg failed: {exc}") from exc

    return sorted(output_dir.glob("seg_*.mp4"))


def _rename_segments(segments: list[Path], base_time: str, segment_seconds: int) -> list[Path]:
    base = datetime.combine(datetime.min.date(), time.fromisoformat(base_time))
    renamed: list[Path] = []
    for i, path in enumerate(segments):
        seg_start = base + timedelta(seconds=i * segment_seconds)
        seg_end = seg_start + timedelta(seconds=segment_seconds)
        name = f"{seg_start:%H-%M-%S}__{seg_end:%H-%M-%S}.mp4"
        new_path = path.with_name(name)
        if new_path.exists():
            raise typer.BadParameter(f"Segment already exists: {new_path}")
        path.rename(new_path)
        renamed.append(new_path)
    return renamed


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
    max_seconds: Optional[float] = None,
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
        result = pipeline.run(video_path, base_ts=base_ts, max_seconds=max_seconds)
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
            result = pipeline.run(video_path, base_ts=segment.start_time, max_seconds=max_seconds)
            events_crud.replace_events_for_segment(session, segment.id, store.id, camera.id, result)
            output = result.to_output(
                segment.to_path_info(store.code, camera.camera_code, settings.timezone),
                settings.timezone,
            )

    if print_json:
        print(json.dumps(output, default=str))


@app.command(name="split-process")
def split_process(
    input_path: str = typer.Option(..., "--input-path"),
    store_code: str = typer.Option(..., "--store-code"),
    camera_code: str = typer.Option(..., "--camera-code"),
    date: str = typer.Option(..., "--date"),
    base_time: str = "00:00:00",
    segment_minutes: int = 5,
    fps: int = 8,
    scale: str = "640:-2",
    crf: int = 28,
    preset: str = "veryfast",
    output_json: Optional[str] = None,
    max_seconds: Optional[float] = None,
) -> None:
    configure_logging()
    settings = get_settings()
    output_dir = (
        Path(settings.video_root) / f"store={store_code}" / f"camera={camera_code}" / f"date={date}"
    )
    segment_seconds = segment_minutes * 60

    segments = _split_with_ffmpeg(
        Path(input_path),
        output_dir,
        segment_seconds=segment_seconds,
        fps=fps,
        scale=scale,
        crf=crf,
        preset=preset,
    )
    if not segments:
        raise typer.BadParameter("No segments produced by ffmpeg")

    segments = _rename_segments(segments, base_time, segment_seconds)

    camera_cfg = load_camera_config(settings.config_dir, store_code, camera_code)
    pipeline = build_pipeline(camera_cfg)
    output_path = Path(output_json or f"var/outputs/{store_code}_{camera_code}_{date}.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary = {"in": 0, "out": 0, "staff_in": 0, "staff_out": 0}
    with output_path.open("w", encoding="utf-8") as f:
        for segment_path in segments:
            info = parse_video_path(segment_path, Path(settings.video_root))
            base_ts = combine_date_time(info.date, info.start_time, settings.timezone)
            result = pipeline.run(segment_path, base_ts=base_ts, max_seconds=max_seconds)
            output = result.to_output(info, settings.timezone)
            counts = output.get("counts", {})
            for key in summary:
                summary[key] += int(counts.get(key, 0))
            f.write(json.dumps(output, default=str) + "\n")

    rprint(f"[green]Segments processed: {len(segments)}[/green]")
    rprint(f"[green]JSONL saved to: {output_path}[/green]")
    rprint(f"[green]Totals: {summary}[/green]")


@app.command(name="merge-jsonl")
def merge_jsonl(
    input_path: str = typer.Option(..., "--input-path"),
    output_path: str = typer.Option(..., "--output-path"),
    include_events: bool = True,
    include_presence: bool = True,
) -> None:
    merged = {
        "source": {
            "input": input_path,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "totals": {"in": 0, "out": 0, "staff_in": 0, "staff_out": 0},
        "segments": [],
    }

    with Path(input_path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            segment = json.loads(line)
            counts = segment.get("counts", {})
            for key in merged["totals"]:
                merged["totals"][key] += int(counts.get(key, 0))

            if not include_events:
                segment["events"] = []
            if not include_presence:
                segment["presence_samples"] = []
            merged["segments"].append(segment)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(output_path).open("w", encoding="utf-8") as f:
        json.dump(merged, f, default=str)

    rprint(f"[green]Merged JSON saved to: {output_path}[/green]")

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
