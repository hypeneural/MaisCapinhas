# Mais Capinhas People Analytics - JSON para Front-end

Este documento explica o formato do JSON gerado pelo pipeline de video para consumo no dashboard.

## Formatos de arquivo

1) JSONL (um JSON por linha)
- Arquivo: `*.jsonl`
- Cada linha representa 1 segmento de video (ex: 5 minutos).
- Vantagem: leitura incremental/streaming e arquivos menores por linha.

2) JSON merge (arquivo unico)
- Arquivo: `*.json`
- Contem um resumo geral + todos os segmentos.
- Vantagem: leitura unica no front.

## Estrutura do JSON (merge)

```
{
  "source": {
    "input": "var/outputs/tabuleiro_full.jsonl",
    "generated_at": "2025-12-31T16:18:33.093301+00:00"
  },
  "totals": {
    "in": 20,
    "out": 19,
    "staff_in": 0,
    "staff_out": 0
  },
  "segments": [
    {
      "segment": {
        "store_code": "001",
        "camera_code": "entrance",
        "start_time": "2025-12-31T10:00:00-03:00",
        "end_time": "2025-12-31T10:05:00-03:00"
      },
      "counts": {
        "in": 3,
        "out": 2,
        "staff_in": 0,
        "staff_out": 0
      },
      "events": [
        {
          "ts": "2025-12-31 10:01:13.375000-03:00",
          "direction": "IN",
          "track_id": "1",
          "confidence": 0.81
        }
      ],
      "presence_samples": [],
      "meta": {
        "frames_read": 2500,
        "duration_s": 312.375,
        "errors": []
      }
    }
  ]
}
```

## Campos e tipos (detalhe)

### source
- `input` (string): caminho do JSONL usado como base do merge.
- `generated_at` (string, ISO-8601): data/hora da geracao do merge.

### totals
Resumo geral somando todos os segmentos:
- `in` (int): total de entradas.
- `out` (int): total de saidas.
- `staff_in` (int): entradas de funcionario (atualmente 0, staff ainda nao ativo).
- `staff_out` (int): saidas de funcionario (atualmente 0).

### segments (lista)
Cada item representa um segmento de video.

#### segments[].segment
- `store_code` (string)
- `camera_code` (string)
- `start_time` (string, ISO-8601 com timezone)
- `end_time` (string, ISO-8601 com timezone)

#### segments[].counts
Contagem agregada do segmento:
- `in` (int)
- `out` (int)
- `staff_in` (int)
- `staff_out` (int)

#### segments[].events
Eventos brutos (opcional para dashboards detalhados):
- `ts` (string, ISO-8601 com timezone)
- `direction` (string): "IN" ou "OUT"
- `track_id` (string): id do tracker (nao e pessoa real, apenas identificador temporario)
- `confidence` (float): confianca da deteccao

#### segments[].presence_samples
Lista para amostragem de ocupacao (ainda vazio no MVP):
- `ts` (string, ISO-8601)
- `count` (int)

#### segments[].meta
Info tecnica do processamento:
- `frames_read` (int)
- `duration_s` (float)
- `errors` (lista de strings)

## Como o front deve consumir

1) **KPIs gerais**
- Usar `totals` para cards de resumo (entradas/saidas).

2) **Time series**
- Usar `segments[].segment.start_time` como eixo temporal.
- Usar `segments[].counts.in` e `segments[].counts.out` para grafico por bloco (5 min).

3) **Eventos detalhados (debug)**
- Usar `segments[].events` para tabela ou auditoria.
- `track_id` pode repetir e nao deve ser tratado como cliente unico.

4) **Alertas de erro**
- Se `segments[].meta.errors` nao estiver vazio, marcar segmento como "falha parcial".

## Observacoes importantes

- Timezone sempre vem no timestamp (ex: `-03:00`).
- `staff_in/out` sera 0 ate ativarmos exclusao de funcionarios.
- `IN/OUT` depende da direcao configurada da linha; se estiver invertido, ajustar config.
- Eventos podem ter entrada/saida repetida do mesmo track em poucos segundos; use filtros no front se necessario.

## JSONL (formato linha a linha)

Cada linha do `.jsonl` e o mesmo objeto de `segments[]`.  
O front pode ler o arquivo em streaming ou converter para o formato merge.
