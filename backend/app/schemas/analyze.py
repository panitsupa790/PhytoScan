from typing import Literal

from pydantic import BaseModel, Field

from app.core.errors import ErrorCode


class PlantPrediction(BaseModel):
    code: str
    name_th: str
    name_en: str
    confidence: float = Field(ge=0.0, le=1.0)


class DiseasePrediction(BaseModel):
    code: str
    name_th: str
    name_en: str
    confidence: float = Field(ge=0.0, le=1.0)


class ImageAnalyzeResult(BaseModel):
    index: int = Field(ge=0, le=2)
    filename: str
    disease: DiseasePrediction
    symptoms: list[str]
    care: list[str]
    prevention: list[str]


class ImagePlantPrediction(BaseModel):
    index: int = Field(ge=0, le=2)
    filename: str
    plant: PlantPrediction
    margin: float = Field(ge=0.0, le=1.0)
    accepted: bool
    reasons: list[Literal["low_confidence", "low_margin"]] = Field(
        default_factory=list
    )


class AnalyzeResponse(BaseModel):
    success: Literal[True] = True
    status: Literal["completed"] = "completed"
    image_count: int = Field(ge=1, le=3)
    plant: PlantPrediction
    disease: DiseasePrediction
    symptoms: list[str]
    care: list[str]
    prevention: list[str]
    image_results: list[ImageAnalyzeResult] = Field(default_factory=list)


class ManualConfirmationResponse(BaseModel):
    success: Literal[False] = False
    status: Literal["manual_confirmation_required"] = "manual_confirmation_required"
    message: str
    suggested_plant: PlantPrediction | None = None
    image_predictions: list[ImagePlantPrediction]
    reasons: list[
        Literal["low_confidence", "low_margin", "inconsistent_plant"]
    ]


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    error_code: ErrorCode
    message: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str


class PlantSummary(BaseModel):
    code: str
    name_th: str
    name_en: str
    disease_count: int = Field(ge=1)


class PlantsResponse(BaseModel):
    plants: list[PlantSummary]
