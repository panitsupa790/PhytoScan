from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Header, Request, status

from app.core.errors import APIError, ErrorCode
from app.db.database import database_connection


DEVICE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")


@dataclass(frozen=True)
class ClientIdentity:
    user_id: str | None = None
    device_id: str | None = None


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _database_path(request: Request) -> Path | None:
    return getattr(request.app.state, "database_path", None)


def register_device(
    device_id: str,
    *,
    database_path: str | Path | None = None,
    platform: str | None = None,
    app_version: str | None = None,
) -> None:
    now = _now()
    with database_connection(database_path) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO devices(
                    id, platform, app_version, created_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    platform = COALESCE(excluded.platform, devices.platform),
                    app_version = COALESCE(excluded.app_version, devices.app_version),
                    last_seen_at = excluded.last_seen_at
                """,
                (device_id, platform, app_version, now, now),
            )


async def resolve_client_identity(
    request: Request,
    x_device_id: str | None = Header(default=None, alias="X-Device-ID"),
    x_client_platform: str | None = Header(default=None, alias="X-Client-Platform"),
    x_app_version: str | None = Header(default=None, alias="X-App-Version"),
) -> ClientIdentity:
    if x_device_id is None or not x_device_id.strip():
        return ClientIdentity()
    device_id = x_device_id.strip()
    if DEVICE_ID_PATTERN.fullmatch(device_id) is None:
        raise APIError(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.invalid_device_id,
            "Invalid device identifier",
        )
    register_device(
        device_id,
        database_path=_database_path(request),
        platform=x_client_platform,
        app_version=x_app_version,
    )
    return ClientIdentity(device_id=device_id)
