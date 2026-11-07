from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class NumericRange(BaseModel):
    min: float | None = None
    max: float | None = None


class PlantTaxonomy(BaseModel):
    scientific_name: str
    family: str
    genus: str
    species_or_cultivar_notes: str


class PlantOverview(BaseModel):
    summary_th: str
    summary_en: str
    origin: str
    growth_habit: str
    typical_height_cm: NumericRange


class PlantIdentification(BaseModel):
    leaf_shape: list[str]
    leaf_color: list[str]
    stem_features: list[str]
    flower_features: list[str]
    distinguishing_features: list[str]


class CareSection(BaseModel):
    level: str | None = None
    frequency: str | None = None
    type: str | None = None
    details: str
    warning_signs: list[str] = Field(default_factory=list)
    ph_range: NumericRange | None = None


class TemperatureSection(BaseModel):
    min: float | None = None
    max: float | None = None
    details: str


class PlantCare(BaseModel):
    light: CareSection
    watering: CareSection
    soil: CareSection
    temperature_c: TemperatureSection
    humidity: CareSection
    fertilizer: CareSection
    pruning: str
    repotting: str


class PlantSafety(BaseModel):
    toxicity_humans: str
    toxicity_pets: str
    handling_notes: list[str]


class PlantScanGuidance(BaseModel):
    recommended_parts: list[str]
    capture_tips: list[str]
    avoid: list[str]


class PlantGalleryImage(BaseModel):
    image: HttpUrl
    alt_text_th: str
    source: HttpUrl
    license: str
    attribution: str


class PlantMedia(BaseModel):
    cover_image: HttpUrl
    cover_alt_text_th: str
    gallery: list[PlantGalleryImage]
    source: HttpUrl
    license: str


class PlantSource(BaseModel):
    title: str
    url: HttpUrl
    type: str


class PlantReview(BaseModel):
    status: str
    reviewed_by: str
    reviewed_at: str | None = None


class PlantLibrarySummary(BaseModel):
    plant_code: str
    name_th: str
    name_en: str
    scientific_name: str
    summary_th: str
    cover_image: HttpUrl
    cover_alt_text_th: str
    supported_disease_count: int = Field(ge=0)
    review_status: str


class PlantLibraryListResponse(BaseModel):
    plants: list[PlantLibrarySummary]


class PlantLibraryDetail(BaseModel):
    plant_code: str
    name_th: str
    name_en: str
    other_names_th: list[str]
    other_names_en: list[str]
    taxonomy: PlantTaxonomy
    overview: PlantOverview
    identification: PlantIdentification
    care: PlantCare
    safety: PlantSafety
    scan_guidance: PlantScanGuidance
    supported_disease_codes: list[str]
    media: PlantMedia
    sources: list[PlantSource]
    review: PlantReview
