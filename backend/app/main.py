from fastapi import FastAPI

from app.modules.auth.router import router as auth_router
from app.modules.health.router import router as health_router

app = FastAPI(title="registro-venta-micro API")

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
