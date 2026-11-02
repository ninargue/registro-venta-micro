from fastapi import FastAPI

from app.modules.health.router import router as health_router

app = FastAPI(title="registro-venta-micro API")

app.include_router(health_router, prefix="/api/v1")
