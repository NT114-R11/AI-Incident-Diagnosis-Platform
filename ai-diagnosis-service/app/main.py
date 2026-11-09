from fastapi import FastAPI
from app.routers.health import router as health_router
from app.routers.alertmanager import router as alertmanager_router
from app.routers.incidents import router as incidents_router
app = FastAPI(
    title="AI Diagnosis Service",
    description="AI-assisted incident diagnosis service",
    version="1.0.0"
)

app.include_router(health_router)
app.include_router(alertmanager_router)
app.include_router(incidents_router)