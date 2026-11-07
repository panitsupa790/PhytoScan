from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from starlette.concurrency import run_in_threadpool

from app.core.errors import APIError, ErrorCode
from app.db.history_repository import (
    clear_history,
    delete_history,
    get_history,
    list_history,
)
from app.schemas.history import (
    DeleteHistoryResponse,
    ScanHistoryDetail,
    ScanHistoryListResponse,
)
from app.services.client_identity import ClientIdentity, resolve_client_identity


router = APIRouter(prefix="/history", tags=["history"])


def _require_owner(identity: ClientIdentity) -> None:
    if identity.user_id is None and identity.device_id is None:
        raise APIError(
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.authentication_required,
            "A device identifier or authenticated account is required",
        )


@router.get("", response_model=ScanHistoryListResponse)
async def scan_history(
    request: Request,
    identity: Annotated[ClientIdentity, Depends(resolve_client_identity)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ScanHistoryListResponse:
    _require_owner(identity)
    items, total = await run_in_threadpool(
        list_history,
        user_id=identity.user_id,
        device_id=identity.device_id,
        limit=limit,
        offset=offset,
        database_path=request.app.state.database_path,
    )
    return ScanHistoryListResponse(
        items=items, total=total, limit=limit, offset=offset
    )


@router.get("/{scan_id}", response_model=ScanHistoryDetail)
async def scan_history_detail(
    scan_id: str,
    request: Request,
    identity: Annotated[ClientIdentity, Depends(resolve_client_identity)],
) -> ScanHistoryDetail:
    _require_owner(identity)
    item = await run_in_threadpool(
        get_history,
        scan_id,
        user_id=identity.user_id,
        device_id=identity.device_id,
        database_path=request.app.state.database_path,
    )
    if item is None:
        raise APIError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.history_not_found,
            "Scan history was not found",
        )
    return ScanHistoryDetail.model_validate(item)


@router.delete("/{scan_id}", response_model=DeleteHistoryResponse)
async def remove_scan_history(
    scan_id: str,
    request: Request,
    identity: Annotated[ClientIdentity, Depends(resolve_client_identity)],
) -> DeleteHistoryResponse:
    _require_owner(identity)
    deleted = await run_in_threadpool(
        delete_history,
        scan_id,
        user_id=identity.user_id,
        device_id=identity.device_id,
        database_path=request.app.state.database_path,
    )
    if deleted == 0:
        raise APIError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.history_not_found,
            "Scan history was not found",
        )
    return DeleteHistoryResponse(deleted_count=deleted)


@router.delete("", response_model=DeleteHistoryResponse)
async def remove_all_scan_history(
    request: Request,
    identity: Annotated[ClientIdentity, Depends(resolve_client_identity)],
) -> DeleteHistoryResponse:
    _require_owner(identity)
    deleted = await run_in_threadpool(
        clear_history,
        user_id=identity.user_id,
        device_id=identity.device_id,
        database_path=request.app.state.database_path,
    )
    return DeleteHistoryResponse(deleted_count=deleted)
