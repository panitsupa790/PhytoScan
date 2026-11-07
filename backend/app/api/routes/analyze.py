#  ./backend/app/api/routes/analyze.py

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.core.errors import APIError, ErrorCode
from app.db.analysis_repository import record_analysis
from app.schemas.analyze import (
    AnalyzeResponse,
    ErrorResponse,
    ManualConfirmationResponse,
    PlantsResponse,
)
from app.services.analysis_router import analyze_automatically, analyze_confirmed
from app.services.model_registry import (
    UnsupportedPlantError,
    get_plant_config,
    list_supported_plants,
)
from app.services.plant_model_service import (
    InferenceError,
    ModelUnavailableError,
)
from app.services.plant_classifier_service import (
    ClassifierInferenceError,
    ClassifierUnavailableError,
)
from app.services.image_service import validate_images
from app.services.client_identity import ClientIdentity, resolve_client_identity


router = APIRouter(tags=["analysis"])
logger = logging.getLogger(__name__)


@router.get("/plants", response_model=PlantsResponse, tags=["plants"])
async def supported_plants() -> PlantsResponse:
    return PlantsResponse(plants=list_supported_plants())


@router.post(
    "/analyze",
    response_model=AnalyzeResponse | ManualConfirmationResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def analyze_images(
    request: Request,
    response: Response,
    identity: Annotated[ClientIdentity, Depends(resolve_client_identity)],
    plant_code: Annotated[
        str | None,
        Form(description="Optional manually confirmed plant code"),
    ] = None,
    images: Annotated[
        list[UploadFile] | None,
        File(description="One to three JPG, JPEG, or PNG plant images"),
    ] = None,
) -> AnalyzeResponse | ManualConfirmationResponse:
    config = None
    if plant_code is not None:
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
        if config is not None:
            result = await run_in_threadpool(
                analyze_confirmed, validated_images, config.plant_code
            )
        else:
            result = await run_in_threadpool(analyze_automatically, validated_images)
    except (ModelUnavailableError, ClassifierUnavailableError):
        raise APIError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.model_unavailable,
            "Plant analysis model is unavailable",
        ) from None
    except (InferenceError, ClassifierInferenceError):
        raise APIError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCode.inference_failed,
            "Plant image analysis failed",
        ) from None
    try:
        scan_id = await run_in_threadpool(
            record_analysis,
            validated_images,
            result,
            plant_code,
            database_path=request.app.state.database_path,
            user_id=identity.user_id,
            device_id=identity.device_id,
        )
        response.headers["X-Scan-ID"] = scan_id
    except Exception:
        # Database history is deliberately best-effort so a storage outage does not
        # replace a valid inference response with an unrelated server error.
        logger.exception("Unable to persist plant analysis outcome")
    return result
