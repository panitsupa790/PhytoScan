from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Sequence

import numpy as np
import tensorflow as tf
from app.services.image_service import ValidatedImage
from app.services.model_input import ModelInputError, prepare_model_input
from app.services.model_registry import PlantClassifierConfig, get_classifier_config


class ClassifierUnavailableError(RuntimeError):
    pass


class ClassifierInferenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class PlantClassPrediction:
    plant_code: str
    class_index: int
    confidence: float
    margin: float
    probabilities: dict[str, float]


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class PlantClassifierService:
    def __init__(self, config: PlantClassifierConfig, model: Any | None = None) -> None:
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
                raise ClassifierUnavailableError("Classifier file does not exist")
            if _sha256(self.config.model_path) != self.config.sha256:
                raise ClassifierUnavailableError("Classifier checksum mismatch")
            model = tf.keras.models.load_model(self.config.model_path, compile=False)
            self._validate_model(model)
            return model
        except ClassifierUnavailableError:
            raise
        except Exception as error:
            raise ClassifierUnavailableError("Could not load plant classifier") from error

    def _validate_model(self, model: Any) -> None:
        if tuple(int(value) for value in model.input_shape[1:]) != self.config.input_shape:
            raise ClassifierUnavailableError("Classifier input shape does not match manifest")
        if int(model.output_shape[-1]) != len(self.class_names):
            raise ClassifierUnavailableError("Classifier output count does not match class order")

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
            raise ClassifierInferenceError("Validated image could not be preprocessed") from error

    def predict_many(self, images: Sequence[ValidatedImage]) -> tuple[PlantClassPrediction, ...]:
        if not 1 <= len(images) <= 3:
            raise ClassifierInferenceError("Inference requires one to three images")
        batch = np.stack([self._prepare(image) for image in images])
        try:
            with self._inference_lock:
                output = self.model(batch, training=False)
            probabilities = np.asarray(output, dtype=np.float32)
        except ClassifierUnavailableError:
            raise
        except Exception as error:
            raise ClassifierInferenceError("Plant classifier inference failed") from error
        expected_shape = (len(images), len(self.class_names))
        if probabilities.shape != expected_shape:
            raise ClassifierInferenceError("Classifier returned an invalid probability shape")
        if not np.isfinite(probabilities).all() or not np.allclose(
            probabilities.sum(axis=1), 1.0, atol=1e-5
        ):
            raise ClassifierInferenceError("Classifier returned invalid probabilities")
        return tuple(self._to_prediction(row) for row in probabilities)

    def _to_prediction(self, row: np.ndarray) -> PlantClassPrediction:
        order = np.argsort(row)
        top_index = int(order[-1])
        second_index = int(order[-2])
        values = {
            name: float(row[index]) for index, name in enumerate(self.class_names)
        }
        return PlantClassPrediction(
            plant_code=self.class_names[top_index],
            class_index=top_index,
            confidence=values[self.class_names[top_index]],
            margin=float(row[top_index] - row[second_index]),
            probabilities=values,
        )


@lru_cache(maxsize=1)
def get_plant_classifier_service() -> PlantClassifierService:
    return PlantClassifierService(get_classifier_config())
