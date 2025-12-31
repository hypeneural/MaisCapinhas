# Mais Capinhas - People Analytics (KPIs via Video)

Projeto para gerar KPIs de fluxo a partir de videos brutos das lojas Mais Capinhas.
Pipeline offline, multi-loja/multi-camera, com fila de jobs no banco e saida em JSON/KPIs.

## Objetivo

- Transformar video em eventos de entrada/saida por camera e por loja.
- Consolidar KPIs por hora e por turno para uso em dashboard.
- Manter arquitetura pronta para atributos (sexo/idade), reid e recorrencia no futuro.

## Status atual (MVP pronto para operar)

- Estrutura de pastas por store/camera/date (nao depende do nome do arquivo).
- Ingest com dedup e criacao de `video_segments`.
- Fila de jobs no banco (sem Redis) com `SELECT ... FOR UPDATE SKIP LOCKED`.
- Worker para `PROCESS_SEGMENT` e `KPI_REBUILD`.
- Pipeline modular: detect -> track -> line count -> extract_faces -> staff exclusion (stub).
- Saida JSON por segmento, JSONL e merge JSON para dashboard (inclui face_captures).
- FastAPI basica (health, stores, segments, kpis).
- Script de split via ffmpeg e comando `split-process`.

## Analise do workflow atual (fluxo completo)

1) Videos entram no padrao de pastas `store=.../camera=.../date=.../HH-MM-SS__HH-MM-SS.ext`.
2) `ingest` varre o `video_root`, cria `video_segments` e enfileira `PROCESS_SEGMENT`.
3) Worker faz claim do job, processa o segmento e grava eventos em `people_flow_events`.
4) Worker cria job `KPI_REBUILD` para a data do segmento.
5) KPI rebuild consolida dados em `kpi_hourly` e `kpi_shift`.
6) Para uso rapido, `process` e `split-process` geram JSON/JSONL para dashboard.

## Arquitetura e componentes

- `apps/cli.py`: comandos de ingest, process, split-process, merge-jsonl e init-db.
- `apps/worker/worker.py`: loop de jobs no banco (claim + retry).
- `apps/api/`: API FastAPI para painel/admin.
- `src/people_analytics/vision/`: pipeline de visao computacional.
- `src/people_analytics/db/`: modelos, CRUD e sessao SQLAlchemy.
- `config/`: stores, cameras e shifts.

## Estrutura do repositorio

```
apps/
  cli.py                 CLI (ingest, process, split-process, merge-jsonl)
  api/                   FastAPI (health, stores, segments, kpis)
  worker/                worker que consome jobs do DB

src/people_analytics/
  core/                  settings, config, logging, time utils
  storage/               parser de path, scanner, fingerprint
  db/                    models, crud, session
  vision/                pipeline + stages (detect, track, count, staff)
  kpi/                   aggregators e rebuild

config/                  stores, cameras, shifts
scripts/                 split_video.ps1, systemd samples
var/                     logs, cache, debug_frames, videos, outputs
tests/                   testes unitarios
front.md                 contrato JSON para o front-end
```

## Organizacao obrigatoria dos videos

Nao dependa do nome do arquivo. Dependa da estrutura de pastas:

```
var/people_analytics/videos/
  store=001/
    camera=entrance/
      date=2025-12-31/
        10-00-00__10-30-00.dav
        14-00-00__14-10-00.mp4
```

Extensoes suportadas: `.mp4`, `.mkv`, `.avi`, `.dav`.

## Configuracao

Arquivos principais:

- `config/stores.yml` (lojas, timezone, video_root)
- `config/shifts.yml` (turnos)
- `config/cameras/store_001_entrance.yml` (linha, ROI, resize, detecao, tracking)

Parametros de camera mais importantes:

- `line.start` / `line.end`, `line.min_interval_s`, `direction`
- `roi` e `resize` (coordenadas no frame redimensionado)
- `processing.yolo_model`, `conf`, `iou`, `person_class_id`
- `processing.crop_roi` (true para cortar a ROI antes da detecao)
- `tracking.track_thresh`, `tracking.match_thresh`, `tracking.track_buffer`
- `face_capture` (captura de rosto, thresholds e debounce)

Se IN/OUT estiver invertido, troque `line.start`/`line.end` ou altere `direction`.

## Variaveis de ambiente (.env)

Use `.env.example` como base. Principais variaveis:

| Variavel | Default | Descricao |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./var/people_analytics.db` | Banco local para dev |
| `VIDEO_ROOT` | `./var/people_analytics/videos` | Raiz dos videos |
| `FACES_ROOT` | `./var/people_analytics/faces` | Saida das capturas de rosto |
| `CONFIG_DIR` | `./config` | Pasta de configs |
| `TIMEZONE` | `America/Sao_Paulo` | Timezone base |
| `JOB_POLL_INTERVAL` | `5` | Intervalo do worker (s) |
| `JOB_LOCK_TIMEOUT` | `300` | Timeout de lock (s) |

## Banco de dados (tabelas MVP)

- `stores`, `cameras`
- `video_segments` (1 arquivo = 1 segmento)
- `jobs` (fila no DB, sem Redis)
- `people_flow_events` (IN/OUT, staff flag)
- `face_captures` (rostos salvos em disco)
- `metrics_presence` (amostragem de ocupacao, ainda vazio)
- `kpi_hourly`, `kpi_shift`
- `staff` (stub para exclusao)

## Fila de jobs no banco

- Claim com `SELECT ... FOR UPDATE SKIP LOCKED`.
- Lock timeout com requeue de jobs travados.
- Status: queued -> processing -> done/failed.
- Escala com varios workers em paralelo.

## Pipeline de visao (stages)

1) Detect (YOLO) -> detecta pessoas
2) Track (ByteTrack) -> IDs temporarios
3) Line count -> gera eventos IN/OUT
4) Extract faces -> captura rosto + salva em disco
5) Staff exclusion -> hook para excluir funcionarios (stub)

Observacao: o `crop_roi` corta a ROI antes da deteccao e acelera muito em CPU.

## Saida de dados

### JSON por segmento (stdout ou JSONL)

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

### JSON merge (dashboard)

Use `merge-jsonl` para gerar um arquivo unico com `totals` + `segments`.
Veja `front.md` para o contrato completo do JSON.

## Comandos CLI (principais)

```
python -m apps.cli init-db
python -m apps.cli ingest
python -m apps.cli process --path <video_file>
python -m apps.cli split-process --input-path <video> --store-code 001 --camera-code entrance --date 2025-12-31
python -m apps.cli merge-jsonl --input-path var/outputs/out.jsonl --output-path var/outputs/out.json
python -m apps.cli kpi-rebuild <date> <store_id> [camera_id]
python -m apps.worker.worker
```

Atalho via Makefile:

```
make init-db
make ingest
make worker
make api
```

## Setup local (Windows)

```
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -e .
python -m pip install -e .[vision]
copy .env.example .env
python -m apps.cli init-db
```

Depois:

```
python -m apps.cli ingest
python -m apps.worker.worker
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Workflow rapido com um video unico

1) Copie o video para a estrutura esperada:

```
var/people_analytics/videos/store=001/camera=entrance/date=2025-12-31/10-00-00__10-30-00.dav
```

2) Rode o processamento:

```
python -m apps.cli process --path <video_file> --max-seconds 120
```

## Split + processamento paralelo (videos longos)

Comando integrado (split + contagem + JSONL):

```
python -m apps.cli split-process ^
  --input-path "C:\Users\Anderson\Desktop\MaisCapinhas\tabuleiro.dav" ^
  --store-code 001 ^
  --camera-code entrance ^
  --date 2025-12-31 ^
  --base-time 10:00:00 ^
  --segment-minutes 5 ^
  --fps 6 ^
  --scale 480:-2 ^
  --workers 2 ^
  --output-json var/outputs/001_entrance_2025-12-31.jsonl
```

Script PowerShell (ffmpeg) pronto:

```
.\scripts\split_video.ps1 `
  -Input "C:\Users\Anderson\Desktop\MaisCapinhas\tabuleiro.dav" `
  -OutputDir "C:\Users\Anderson\Desktop\MaisCapinhas\var\people_analytics\videos\store=001\camera=entrance\date=2025-12-31" `
  -BaseTime "10:00:00" `
  -SegmentMinutes 5 `
  -Fps 6 `
  -Scale "480:-2"
```

## Performance (principais alavancas)

1) Segmentar (5-10 min) e paralelizar (2-3 workers).
2) Reduzir FPS (4-8) e resolucao (ex: 480px largura).
3) ROI menor e linha bem posicionada para reduzir falso positivo.
4) `crop_roi` ligado quando a ROI for pequena.
5) YOLOv8n para CPU; GPU acelera muito se disponivel.
6) Evitar reprocesso: use `ingest` + jobs para cache no banco.

## O que precisa melhorar (gaps tecnicos)

- Staff exclusion real (face embeddings, zona/turno ou uniforme).
- Presence sampling (occupancy) para proxy de movimento.
- Segmentacao automatica de videos longos (DVR/NVR).
- Atributos (sexo/idade) com flags LGPD.
- Reid e recorrencia (visitantes repetidos).
- Mais testes (pipeline, tracking, contagem, jobs).
- Observabilidade (logs estruturados, metrics, alertas).

## Proximos passos recomendados (prioridade)

1) Ajustar ROI/linha por camera ate IN/OUT ficar estavel.
2) Implementar staff exclusion por zona/turno (fallback sem face).
3) Ativar presence sampling e KPI de ocupacao.
4) Consolidar KPIs diarios e exportacao para o dashboard.
5) Opcional: GPU e batch para ganhar throughput.

## Checklist de documentacao (README)

- [ ] Objetivo e escopo atual
- [ ] Status do MVP (o que ja funciona)
- [ ] Workflow completo (passo a passo)
- [ ] Estrutura do repositorio e pastas
- [ ] Padrao de videos e configuracao
- [ ] Comandos CLI e setup local
- [ ] Saida JSON e contrato do front
- [ ] Performance e boas praticas
- [ ] Gaps tecnicos e proximos passos

## Pesquisa em partes (fontes internas)

1) CLI e workflow: `apps/cli.py`
2) Worker e jobs: `apps/worker/worker.py`, `src/people_analytics/db/crud/jobs.py`
3) Pipeline e stages: `src/people_analytics/vision/*`
4) Configs e paths: `config/*`, `src/people_analytics/storage/*`
5) Banco e modelos: `src/people_analytics/db/models/*`
6) Output JSON: `front.md`

## Observacoes importantes

- Evite commitar videos no Git (use `var/` ou Git LFS).
- `tzdata` e necessario no Windows para timezone.
- Staff por face falha se a camera nao captura rosto frontal.
