#  ./backend/app/api/routes/analyze.py

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.core.errors import APIError, ErrorCode
from app.schemas.analyze import AnalyzeResponse, ErrorResponse, PlantsResponse
from app.services.model_registry import (
    UnsupportedPlantError,
    get_plant_config,
    list_supported_plants,
)
from app.services.plant_model_service import (
    InferenceError,
    ModelUnavailableError,
    get_model_service,
)
from app.services.image_service import validate_images


router = APIRouter(tags=["analysis"])


@router.get("/plants", response_model=PlantsResponse, tags=["plants"])
async def supported_plants() -> PlantsResponse:
    return PlantsResponse(plants=list_supported_plants())


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def analyze_images(
    plant_code: Annotated[str, Form(description="Selected plant code")],
    images: Annotated[
        list[UploadFile] | None,
        File(description="One to three JPG, JPEG, or PNG plant images"),
    ] = None,
) -> AnalyzeResponse:
    try:
        config = get_plant_config(plant_code)
    except UnsupportedPlantError:
        raise APIError(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.unsupported_plant,
            "Unsupported plant code",
        ) from None
    validated_images = await validate_images(images)
    try:
        service = get_model_service(config.plant_code)
        return await run_in_threadpool(service.analyze, validated_images)
    except ModelUnavailableError:
        raise APIError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.model_unavailable,
            "Plant analysis model is unavailable",
        ) from None
    except InferenceError:
        raise APIError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCode.inference_failed,
            "Plant image analysis failed",
        ) from None
