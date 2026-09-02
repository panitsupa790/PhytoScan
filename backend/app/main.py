from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.analyze import router as analyze_router
from app.core.config import settings
from app.core.errors import APIError, api_error_handler
from app.schemas.analyze import HealthResponse


app = FastAPI(
    title=settings.app_name,
    description="Backend MVP for plant image analysis.",
    version="0.1.0",
)

app.add_exception_handler(APIError, api_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(analyze_router, prefix=settings.api_v1_prefix)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(service=settings.app_name)
