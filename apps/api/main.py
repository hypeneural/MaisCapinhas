from fastapi import FastAPI

from apps.api.routers import health, kpis, segments, stores

app = FastAPI(title="People Analytics")

app.include_router(health.router)
app.include_router(stores.router, prefix="/stores", tags=["stores"])
app.include_router(segments.router, prefix="/segments", tags=["segments"])
app.include_router(kpis.router, prefix="/kpis", tags=["kpis"])
