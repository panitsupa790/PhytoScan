import json
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from app.schemas.analyze import AnalyzeResponse, DiseasePrediction, PlantPrediction
from app.services.image_service import ValidatedImage


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "diseases.json"


@lru_cache(maxsize=1)
def _load_disease_data() -> dict[str, dict[str, dict[str, object]]]:
    with DATA_FILE.open(encoding="utf-8") as data_file:
        return json.load(data_file)


class MockAIService:
    """Temporary predictor with the same boundary expected from a real AI service."""

    def analyze(self, images: Sequence[ValidatedImage]) -> AnalyzeResponse:
        # A real service will predict each image, validate plant consistency,
        # aggregate predictions, then look up the selected disease record here.
        disease = _load_disease_data()["eggplant"]["leaf_spot"]

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
