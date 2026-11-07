from __future__ import annotations

from collections.abc import Sequence

from app.schemas.analyze import (
    AnalyzeResponse,
    ImagePlantPrediction,
    ManualConfirmationResponse,
    PlantPrediction,
)
from app.services.image_service import ValidatedImage
from app.services.model_registry import get_plant_config
from app.services.plant_classifier_service import (
    ClassifierUnavailableError,
    PlantClassPrediction,
    get_plant_classifier_service,
)
from app.services.plant_model_service import get_model_service
from app.services.threshold_config import PlantThresholds, get_plant_thresholds


AnalysisResult = AnalyzeResponse | ManualConfirmationResponse


def _plant_prediction(prediction: PlantClassPrediction) -> PlantPrediction:
    config = get_plant_config(prediction.plant_code)
    return PlantPrediction(
        code=config.plant_code,
        name_th=config.name_th,
        name_en=config.name_en,
        confidence=prediction.confidence,
    )


def _manual_confirmation(
    images: Sequence[ValidatedImage],
    predictions: Sequence[PlantClassPrediction],
    thresholds: PlantThresholds,
) -> ManualConfirmationResponse:
    plant_codes = {prediction.plant_code for prediction in predictions}
    inconsistent = len(plant_codes) != 1
    image_predictions: list[ImagePlantPrediction] = []
    overall_reasons: list[str] = []
    for index, (image, prediction) in enumerate(zip(images, predictions)):
        reasons = []
        if prediction.confidence < thresholds.min_confidence:
            reasons.append("low_confidence")
        if prediction.margin < thresholds.min_margin:
            reasons.append("low_margin")
        for reason in reasons:
            if reason not in overall_reasons:
                overall_reasons.append(reason)
        image_predictions.append(
            ImagePlantPrediction(
                index=index,
                filename=image.filename,
                plant=_plant_prediction(prediction),
                margin=prediction.margin,
                accepted=not reasons and not inconsistent,
                reasons=reasons,
            )
        )
    if inconsistent:
        overall_reasons.append("inconsistent_plant")
    suggested = _plant_prediction(predictions[0]) if not inconsistent else None
    return ManualConfirmationResponse(
        message="Please confirm the plant type before disease analysis",
        suggested_plant=suggested,
        image_predictions=image_predictions,
        reasons=overall_reasons,
    )


def analyze_automatically(images: Sequence[ValidatedImage]) -> AnalysisResult:
    classifier = get_plant_classifier_service()
    try:
        thresholds = get_plant_thresholds()
    except ValueError as error:
        raise ClassifierUnavailableError("Threshold configuration is unavailable") from error
    predictions = classifier.predict_many(images)
    accepted = all(
        prediction.confidence >= thresholds.min_confidence
        and prediction.margin >= thresholds.min_margin
        for prediction in predictions
    )
    same_plant = len({prediction.plant_code for prediction in predictions}) == 1
    if not accepted or not same_plant:
        return _manual_confirmation(images, predictions, thresholds)
    plant_code = predictions[0].plant_code
    conservative_confidence = min(prediction.confidence for prediction in predictions)
    return get_model_service(plant_code).analyze(images, conservative_confidence)


def analyze_confirmed(
    images: Sequence[ValidatedImage], plant_code: str
) -> AnalyzeResponse:
    return get_model_service(plant_code).analyze(images, 1.0)
