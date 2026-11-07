from enum import Enum

from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    invalid_image = "INVALID_IMAGE"
    unsupported_file_type = "UNSUPPORTED_FILE_TYPE"
    too_many_images = "TOO_MANY_IMAGES"
    no_images = "NO_IMAGES"
    file_too_large = "FILE_TOO_LARGE"
    low_confidence = "LOW_CONFIDENCE"
    unsupported_plant = "UNSUPPORTED_PLANT"
    multiple_plant_types = "MULTIPLE_PLANT_TYPES"
    model_unavailable = "MODEL_UNAVAILABLE"
    inference_failed = "INFERENCE_FAILED"
    invalid_device_id = "INVALID_DEVICE_ID"
    authentication_required = "AUTHENTICATION_REQUIRED"
    invalid_credentials = "INVALID_CREDENTIALS"
    email_already_registered = "EMAIL_ALREADY_REGISTERED"
    history_not_found = "HISTORY_NOT_FOUND"
    plant_library_not_found = "PLANT_LIBRARY_NOT_FOUND"


class APIError(Exception):
    def __init__(self, status_code: int, error_code: ErrorCode, message: str) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(message)


async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code.value,
            "message": exc.message,
        },
    )
