# Mais Capinhas — People Analytics (KPIs via Vídeo)

Projeto para gerar KPIs de fluxo a partir de vídeos brutos das lojas Mais Capinhas.  
O pipeline é offline, multi-loja/multi-câmera, com fila de jobs no banco e saída em JSON/KPIs.

## O que já está pronto

- Estrutura multi-loja/multi-câmera baseada em pastas (não depende do nome do arquivo).
- Ingest de vídeos com dedup e criação de `video_segments`.
- Fila de jobs no banco (sem Redis) com `SELECT ... FOR UPDATE SKIP LOCKED`.
- Worker para processar segmentos e disparar rebuild de KPIs.
- Pipeline de visão modular com YOLO (detecção), ByteTrack (tracking) e contagem por linha.
- JSON de saída por vídeo com eventos IN/OUT e métricas básicas.
- KPIs por hora e por turno (hourly/shift) com rebuild.
- API FastAPI (health, stores, segments, kpis).
- Scripts de serviço (systemd) prontos para Linux.

## O que falta fazer (roadmap)

- Exclusão de funcionários (staff) por face embeddings ou por zona/turno.
- Amostragem de presença (occupancy/proxy de movimento).
- Atributos (sexo/idade) com flags LGPD.
- Re-identificação e recorrência.
- Segmentação automática de vídeos longos (quando DVR/NVR não segmenta).
- Otimizações de performance (batch, GPU, amostragem adaptativa).
- Painel/relatórios e alertas operacionais.

## Tecnologias principais

- Python 3.10+
- Pydantic / Pydantic Settings
- SQLAlchemy + Alembic
- FastAPI + Uvicorn
- Typer (CLI)
- OpenCV (leitura de vídeo)
- Ultralytics YOLO (detecção)
- Supervision ByteTrack (tracking)

## Estrutura do repositório

```
apps/
  cli.py                 CLI (ingest, process, kpi-rebuild, staff-rebuild)
  api/                   FastAPI (health, stores, segments, kpis)
  worker/                worker que consome jobs do DB

src/people_analytics/
  core/                  settings, config, time utils
  storage/               parser de path, scanner, fingerprint
  db/                    models, crud, session
  vision/                pipeline + stages (detect, track, count, staff)
  kpi/                   aggregators e rebuild

config/                  stores, cameras, shifts
var/                     logs, cache, debug_frames, videos
scripts/                 serviços systemd (Linux)
tests/                   testes unitários
```

## Estrutura obrigatória dos vídeos

```
/var/people_analytics/videos/
  store=001/
    camera=entrance/
      date=2025-12-31/
        10-00-00__10-30-00.dav
        14-00-00__14-10-00.mp4
```

Extensões suportadas: `.mp4`, `.mkv`, `.avi`, `.dav`.

## Configuração

Arquivos principais:

- `config/stores.yml` (lojas, timezone, video_root)
- `config/shifts.yml` (turnos)
- `config/cameras/store_001_entrance.yml` (linha, ROI, resize, detecção, tracking)

Parâmetros importantes por câmera:

- `line.start` / `line.end`, `line.min_interval_s`, `direction`
- `roi` e `resize` (coordenadas no frame redimensionado)
- `processing.yolo_model`, `conf`, `iou`, `person_class_id`
- `tracking.track_thresh`, `tracking.match_thresh`, `tracking.track_buffer`

Se IN/OUT estiver invertido, troque `line.start`/`line.end` ou altere `direction`.

## Pipeline (fluxo completo)

1) `ingest` escaneia os vídeos e cria `video_segments`.
2) Cada segmento vira um job `PROCESS_SEGMENT`.
3) Worker processa o vídeo: detecção → tracking → contagem por linha.
4) Eventos são gravados em `people_flow_events`.
5) Worker cria job `KPI_REBUILD` para o dia do segmento.
6) KPIs são consolidados em `kpi_hourly` e `kpi_shift`.

## Saída JSON (processamento por vídeo)

```
{
  "segment": {
    "store_code": "001",
    "camera_code": "entrance",
    "start_time": "2025-12-31T10:00:00-03:00",
    "end_time": "2025-12-31T10:30:00-03:00"
  },
  "counts": {
    "in": 3,
    "out": 3,
    "staff_in": 0,
    "staff_out": 0
  },
  "events": [
    {"ts": "...", "direction": "IN", "track_id": "7", "confidence": 0.87}
  ],
  "meta": {
    "frames_read": 900,
    "duration_s": 120.0,
    "errors": []
  }
}
```

## Como rodar local (Windows)

```
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -e .
python -m pip install -e .[vision]
copy .env.example .env
python -m apps.cli init-db
python -m apps.cli ingest
python -m apps.worker.worker
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Teste rápido com um vídeo

1) Copie o arquivo para a estrutura esperada:

```
var/people_analytics/videos/store=001/camera=entrance/date=2025-12-31/10-00-00__10-30-00.dav
```

2) Rode o processamento com tempo limitado:

```
python -m apps.cli process --path <video_file> --max-seconds 120
```

## Otimização para vídeos longos (ex: .dav)

Para reduzir tempo de processamento, recomenda-se converter e fracionar o vídeo em segmentos menores.  
Isso diminui o custo de decodificação e permite paralelizar o worker.

Script pronto (Windows) com ffmpeg:

```
.\scripts\split_video.ps1 `
  -Input "C:\Users\Anderson\Desktop\MaisCapinhas\tabuleiro.dav" `
  -OutputDir "C:\Users\Anderson\Desktop\MaisCapinhas\var\people_analytics\videos\store=001\camera=entrance\date=2025-12-31" `
  -BaseTime "10:00:00" `
  -SegmentMinutes 5 `
  -Fps 8 `
  -Scale "640:-2"
```

Depois do split:

```
python -m apps.cli ingest
python -m apps.worker.worker
```

Dica: ajuste `Fps` e `Scale` para equilibrar qualidade e velocidade, e mantenha `roi/line` no mesmo tamanho do frame redimensionado.

## Workflow integrado (split + contagem + JSON)

Para transformar, fracionar e já gerar JSONL em um único comando:

```
python -m apps.cli split-process ^
  --input-path "C:\Users\Anderson\Desktop\MaisCapinhas\tabuleiro.dav" ^
  --store-code 001 ^
  --camera-code entrance ^
  --date 2025-12-31 ^
  --base-time 10:00:00 ^
  --segment-minutes 5 ^
  --fps 8 ^
  --scale 640:-2 ^
  --output-json var/outputs/001_entrance_2025-12-31.jsonl
```

O arquivo `.jsonl` salva um JSON por segmento (mais leve e fácil de manipular).

## Performance (o que mais impacta)

1) **Segmentar** (5–10 min) e **paralelizar** (mais de um worker).
2) **Reducao de FPS** (4–8) e **resolucao** (ex.: 640px largura).
3) **ROI menor** e **linha bem posicionada** para evitar contagens falsas.
4) **YOLOv8n** (modelo menor) para CPU; GPU acelera bastante se disponivel.
5) Evitar reprocessar: use `ingest` + jobs para cache no banco.

## Observações importantes

- Postgres é recomendado para múltiplos workers.
- SQLite funciona para dev/local.
- Em Windows, `tzdata` é obrigatório para timezone.
- Staff exclusion por face precisa de câmera frontal; se não tiver, use fallback por zona/turno.

## Próximos passos sugeridos

1) Ajustar linha/ROI por câmera até os IN/OUT ficarem corretos.
2) Implementar exclusão de funcionários por zona/escala.
3) Criar segmentador para vídeos longos (DVR/NVR).
4) Ativar presença/ocupação e KPIs avançados.
5) Conectar painel admin e exportações.
