from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Sequence

import numpy as np
import tensorflow as tf
from app.schemas.analyze import (
    AnalyzeResponse,
    DiseasePrediction,
    ImageAnalyzeResult,
    PlantPrediction,
)
from app.services.disease_catalog import get_disease_record
from app.services.image_service import ValidatedImage
from app.services.model_input import ModelInputError, prepare_model_input
from app.services.model_registry import PlantModelConfig, get_plant_config


class ModelUnavailableError(RuntimeError):
    pass


class InferenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImagePrediction:
    class_name: str
    class_index: int
    confidence: float
    probabilities: dict[str, float]


@dataclass(frozen=True)
class AggregatePrediction(ImagePrediction):
    image_predictions: tuple[ImagePrediction, ...]
    aggregation: str = "mean_class_probabilities"


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class PlantModelService:
    def __init__(self, config: PlantModelConfig, model: Any | None = None) -> None:
        self.config = config
        self.class_names = config.class_order
        self._model = model
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self.load_count = 1 if model is not None else 0
        if model is not None:
            self._validate_model(model)

    @property
    def model(self) -> Any:
        if self._model is None:
            with self._load_lock:
                if self._model is None:
                    self._model = self._load_model()
                    self.load_count += 1
        return self._model

    def _load_model(self) -> Any:
        try:
            if not self.config.model_path.is_file():
                raise ModelUnavailableError("Model file does not exist")
            if _sha256(self.config.model_path) != self.config.sha256:
                raise ModelUnavailableError("Model checksum mismatch")
            model = tf.keras.models.load_model(self.config.model_path, compile=False)
            self._validate_model(model)
            return model
        except ModelUnavailableError:
            raise
        except Exception as error:
            raise ModelUnavailableError(
                f"Could not load model for {self.config.plant_code}"
            ) from error

    def _validate_model(self, model: Any) -> None:
        if tuple(int(value) for value in model.input_shape[1:]) != self.config.input_shape:
            raise ModelUnavailableError("Model input shape does not match its manifest")
        if int(model.output_shape[-1]) != len(self.class_names):
            raise ModelUnavailableError("Model output count does not match its class order")

    def _prepare(self, image: ValidatedImage) -> np.ndarray:
        try:
            return prepare_model_input(
                image.content,
                self.config.input_shape,
                self.config.preprocessing,
                self.config.decoder,
                self.config.resize_method,
            )
        except ModelInputError as error:
            raise InferenceError("Validated image could not be preprocessed") from error

    def predict_many(self, images: Sequence[ValidatedImage]) -> AggregatePrediction:
        if not 1 <= len(images) <= 3:
            raise InferenceError("Inference requires one to three images")
        batch = np.stack([self._prepare(image) for image in images])
        try:
            with self._inference_lock:
                output = self.model(batch, training=False)
            probabilities = np.asarray(output, dtype=np.float64)
        except ModelUnavailableError:
            raise
        except Exception as error:
            raise InferenceError("Model inference failed") from error
        expected_shape = (len(images), len(self.class_names))
        if probabilities.shape != expected_shape:
            raise InferenceError("Model returned an invalid probability shape")
        if not np.isfinite(probabilities).all() or not np.allclose(
            probabilities.sum(axis=1), 1.0, atol=1e-5
        ):
            raise InferenceError("Model returned invalid probabilities")
        image_predictions = tuple(self._to_prediction(row) for row in probabilities)
        aggregate = self._to_prediction(probabilities.mean(axis=0))
        return AggregatePrediction(
            class_name=aggregate.class_name,
            class_index=aggregate.class_index,
            confidence=aggregate.confidence,
            probabilities=aggregate.probabilities,
            image_predictions=image_predictions,
        )

    def predict(self, image: ValidatedImage) -> ImagePrediction:
        return self.predict_many([image]).image_predictions[0]

    def _to_prediction(self, probabilities: np.ndarray) -> ImagePrediction:
        index = int(np.argmax(probabilities))
        values = {
            name: float(probabilities[class_index])
            for class_index, name in enumerate(self.class_names)
        }
        return ImagePrediction(
            class_name=self.class_names[index],
            class_index=index,
            confidence=values[self.class_names[index]],
            probabilities=values,
        )

    def analyze(
        self, images: Sequence[ValidatedImage], plant_confidence: float = 1.0
    ) -> AnalyzeResponse:
        prediction = self.predict_many(images)
        try:
            disease = get_disease_record(self.config.plant_code, prediction.class_name)
            image_results = []
            for index, (image, image_prediction) in enumerate(
                zip(images, prediction.image_predictions)
            ):
                image_disease = get_disease_record(
                    self.config.plant_code, image_prediction.class_name
                )
                image_results.append(
                    ImageAnalyzeResult(
                        index=index,
                        filename=image.filename,
                        disease=DiseasePrediction(
                            code=image_prediction.class_name,
                            name_th=str(image_disease["name_th"]),
                            name_en=str(image_disease["name_en"]),
                            confidence=image_prediction.confidence,
                        ),
                        symptoms=list(image_disease["symptoms"]),
                        care=list(image_disease["care"]),
                        prevention=list(image_disease["prevention"]),
                    )
                )
        except ValueError as error:
            raise InferenceError("Disease metadata is unavailable") from error
        return AnalyzeResponse(
            image_count=len(images),
            plant=PlantPrediction(
                code=self.config.plant_code,
                name_th=self.config.name_th,
                name_en=self.config.name_en,
                confidence=plant_confidence,
            ),
            disease=DiseasePrediction(
                code=prediction.class_name,
                name_th=str(disease["name_th"]),
                name_en=str(disease["name_en"]),
                confidence=prediction.confidence,
            ),
            symptoms=list(disease["symptoms"]),
            care=list(disease["care"]),
            prevention=list(disease["prevention"]),
            image_results=image_results,
        )


@lru_cache(maxsize=None)
def get_model_service(plant_code: str) -> PlantModelService:
    return PlantModelService(get_plant_config(plant_code))
