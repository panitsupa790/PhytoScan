from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app.schemas.analyze import AnalyzeResponse, ErrorResponse
from app.services.image_service import validate_images
from app.services.mock_ai_service import mock_ai_service


router = APIRouter(prefix="/analyze", tags=["analysis"])


@router.post(
    "",
    response_model=AnalyzeResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
    },
)
async def analyze_images(
    images: Annotated[
        list[UploadFile] | None,
        File(description="One to three JPG, JPEG, or PNG plant images"),
    ] = None,
) -> AnalyzeResponse:
    validated_images = await validate_images(images)
    return mock_ai_service.analyze(validated_images)
