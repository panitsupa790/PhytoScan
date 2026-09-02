from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Sequence

from fastapi import UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.errors import APIError, ErrorCode


ALLOWED_CONTENT_TYPES = {"image/jpeg": "JPEG", "image/png": "PNG"}
ALLOWED_EXTENSIONS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}


@dataclass(frozen=True)
class ValidatedImage:
    filename: str
    content_type: str
    image_format: str
    size_bytes: int
    width: int
    height: int
    content: bytes


async def validate_images(
    uploads: Sequence[UploadFile] | None,
) -> list[ValidatedImage]:
    if not uploads:
        raise APIError(status.HTTP_400_BAD_REQUEST, ErrorCode.no_images, "กรุณาส่งภาพอย่างน้อย 1 ภาพ")

    if len(uploads) > settings.max_images:
        raise APIError(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.too_many_images,
            f"ส่งภาพได้สูงสุด {settings.max_images} ภาพ",
        )

    validated = []
    for upload in uploads:
        validated.append(await _validate_image(upload))
    return validated


async def _validate_image(upload: UploadFile) -> ValidatedImage:
    filename = upload.filename or ""
    extension = Path(filename).suffix.lower()
    content_type = (upload.content_type or "").lower()

    if extension not in ALLOWED_EXTENSIONS or content_type not in ALLOWED_CONTENT_TYPES:
        await upload.close()
        raise APIError(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            ErrorCode.unsupported_file_type,
            "รองรับเฉพาะไฟล์ JPG, JPEG และ PNG",
        )

    try:
        content = await upload.read(settings.max_image_size_bytes + 1)
    finally:
        await upload.close()

    if len(content) > settings.max_image_size_bytes:
        raise APIError(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            ErrorCode.file_too_large,
            "ไฟล์ภาพมีขนาดใหญ่เกินกำหนด",
        )

    if not content:
        raise APIError(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.invalid_image,
            "ไฟล์ภาพไม่ถูกต้องหรือไฟล์เสีย",
        )

    try:
        with Image.open(BytesIO(content)) as decoded_image:
            actual_format = decoded_image.format
            width, height = decoded_image.size
            decoded_image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise APIError(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.invalid_image,
            "ไฟล์ภาพไม่ถูกต้องหรือไฟล์เสีย",
        ) from None

    if (
        actual_format != ALLOWED_EXTENSIONS[extension]
        or actual_format != ALLOWED_CONTENT_TYPES[content_type]
    ):
        raise APIError(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.invalid_image,
            "ชนิดข้อมูลในไฟล์ไม่ตรงกับนามสกุลหรือ MIME type",
        )

    return ValidatedImage(
        filename=filename,
        content_type=content_type,
        image_format=actual_format,
        size_bytes=len(content),
        width=width,
        height=height,
        content=content,
    )
