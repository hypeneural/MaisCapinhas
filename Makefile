.PHONY: init-db ingest worker api

init-db:
	python -m apps.cli init-db

ingest:
	python -m apps.cli ingest

worker:
	python -m apps.worker.worker

api:
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
