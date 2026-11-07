from __future__ import annotations

from pydantic import BaseModel, Field


class HistoryDiseaseSummary(BaseModel):
    code: str
    name_th: str
    name_en: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ScanHistorySummary(BaseModel):
    id: str
    analyzed_at: str
    plant_code: str
    plant_name_th: str
    plant_name_en: str
    plant_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    plant_source: str
    image_count: int = Field(ge=1, le=3)
    disease_code: str
    disease_name_th: str
    disease_name_en: str
    disease_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    disease_names: list[str]
    diseases: list[HistoryDiseaseSummary]


class ScanHistoryListResponse(BaseModel):
    items: list[ScanHistorySummary]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class HistoryImageResult(BaseModel):
    index: int = Field(ge=0, le=2)
    filename: str
    disease: HistoryDiseaseSummary | None
    symptoms: list[str]
    care: list[str]
    prevention: list[str]


class ScanHistoryDetail(ScanHistorySummary):
    result_agreement: bool | None
    image_results: list[HistoryImageResult]


class DeleteHistoryResponse(BaseModel):
    success: bool = True
    deleted_count: int = Field(ge=0)
