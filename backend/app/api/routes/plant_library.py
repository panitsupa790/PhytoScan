from __future__ import annotations

from fastapi import APIRouter, Request, status
from starlette.concurrency import run_in_threadpool

from app.core.errors import APIError, ErrorCode
from app.db.plant_library_repository import (
    get_plant_library_entry,
    list_plant_library,
)
from app.schemas.plant_library import (
    PlantLibraryDetail,
    PlantLibraryListResponse,
)


router = APIRouter(prefix="/plant-library", tags=["plant-library"])


@router.get("", response_model=PlantLibraryListResponse)
async def plant_library(request: Request) -> PlantLibraryListResponse:
    plants = await run_in_threadpool(
        list_plant_library,
        database_path=request.app.state.database_path,
    )
    return PlantLibraryListResponse(plants=plants)


@router.get("/{plant_code}", response_model=PlantLibraryDetail)
async def plant_library_detail(
    plant_code: str,
    request: Request,
) -> PlantLibraryDetail:
    plant = await run_in_threadpool(
        get_plant_library_entry,
        plant_code,
        database_path=request.app.state.database_path,
    )
    if plant is None:
        raise APIError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.plant_library_not_found,
            "Plant library entry was not found",
        )
    return PlantLibraryDetail.model_validate(plant)
