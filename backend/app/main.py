from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.analyze import router as analyze_router
from app.api.routes.history import router as history_router
from app.api.routes.plant_library import router as plant_library_router
from app.core.config import settings
from app.core.errors import APIError, api_error_handler
from app.db.database import initialize_database, resolve_database_path
from app.schemas.analyze import HealthResponse


@asynccontextmanager
async def lifespan(application: FastAPI):
    initialize_database(application.state.database_path)
    yield


app = FastAPI(
    title=settings.app_name,
    description="PhytoScan Multi-Plant Disease Classification API.",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.database_path = resolve_database_path()

app.add_exception_handler(APIError, api_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Scan-ID"],
)
app.include_router(analyze_router, prefix=settings.api_v1_prefix)
app.include_router(history_router, prefix=settings.api_v1_prefix)
app.include_router(plant_library_router, prefix=settings.api_v1_prefix)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(service=settings.app_name)
