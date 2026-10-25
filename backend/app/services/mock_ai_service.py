from typing import Sequence

from app.schemas.analyze import AnalyzeResponse, DiseasePrediction, PlantPrediction
from app.services.disease_catalog import get_disease_record
from app.services.image_service import ValidatedImage


class MockAIService:
    """Temporary predictor with the same boundary expected from a real AI service."""

    def analyze(self, images: Sequence[ValidatedImage]) -> AnalyzeResponse:
        # A real service will predict each image, validate plant consistency,
        # aggregate predictions, then look up the selected disease record here.
        disease = get_disease_record("eggplant", "leaf_spot")

        return AnalyzeResponse(
            image_count=len(images),
            plant=PlantPrediction(
                code=str(disease["plant_code"]),
                name_th=str(disease["plant_name_th"]),
                name_en=str(disease["plant_name_en"]),
                confidence=0.94,
            ),
            disease=DiseasePrediction(
                code=str(disease["disease_code"]),
                name_th=str(disease["disease_name_th"]),
                name_en=str(disease["disease_name_en"]),
                confidence=0.84,
            ),
            symptoms=list(disease["symptoms"]),
            care=list(disease["care"]),
            prevention=list(disease["prevention"]),
        )


mock_ai_service = MockAIService()
