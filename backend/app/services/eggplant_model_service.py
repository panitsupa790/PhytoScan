#  ./backend/app/services/eggplant_model_service.py

from __future__ import annotations

import hashlib
import json
import sys
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
import tensorflow as tf
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.schemas.analyze import AnalyzeResponse, DiseasePrediction, PlantPrediction
from app.services.disease_catalog import get_disease_record
from app.services.image_service import ValidatedImage


PROJECT_ROOT = Path(__file__).resolve().parents[3]
AI_MODEL_ROOT = PROJECT_ROOT / "ai_model"
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from preprocessing.eggplant import load_config as load_preprocessing_config  # noqa: E402
from preprocessing.eggplant import preprocess_image  # noqa: E402


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_project_path(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


class EggplantModelService:
    def __init__(
        self,
        manifest_path: Path,
        model: Any | None = None,
        preprocess: Callable[[Image.Image, str, dict[str, Any]], Image.Image] = preprocess_image,
    ) -> None:
        self._manifest_path = manifest_path.resolve()
        self._preprocess = preprocess
        self._inference_lock = threading.Lock()
        self.load_count = 0
        started = time.perf_counter()
        try:
            self.manifest = json.loads(self._manifest_path.read_text(encoding="utf-8"))
            self.lock_manifest_path = _resolve_project_path(
                self.manifest["d10_lock_manifest_path"]
            )
            self.config_path = _resolve_project_path(self.manifest["locked_config_path"])
            self.checkpoint_path = _resolve_project_path(self.manifest["checkpoint_path"])
            self.lock_manifest = json.loads(
                self.lock_manifest_path.read_text(encoding="utf-8")
            )
            self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
            self._validate_artifacts()
            self.preprocessing_config = load_preprocessing_config(
                _resolve_project_path(self.config["preprocessing"]["config_path"])
            )
            self.model = model if model is not None else tf.keras.models.load_model(
                self.checkpoint_path, compile=False
            )
            self.load_count = 1
            self._validate_model()
        except ModelUnavailableError:
            raise
        except Exception as error:
            raise ModelUnavailableError("Locked Eggplant v1 artifacts are invalid") from error
        self.load_seconds = time.perf_counter() - started
        self.class_names = tuple(self.config["class_names"])

    def _validate_artifacts(self) -> None:
        if self.manifest["locked_config_sha256"] != self.lock_manifest["final_config_sha256"]:
            raise ModelUnavailableError("Production and D10 config hashes differ")
        if self.manifest["checkpoint_sha256"] != self.lock_manifest["checkpoint_sha256"]:
            raise ModelUnavailableError("Production and D10 checkpoint hashes differ")
        if _sha256(self.config_path) != self.manifest["locked_config_sha256"]:
            raise ModelUnavailableError("Locked config hash mismatch")
        if _sha256(self.checkpoint_path) != self.manifest["checkpoint_sha256"]:
            raise ModelUnavailableError("Locked checkpoint hash mismatch")
        if self.config["checkpoint_sha256"] != self.manifest["checkpoint_sha256"]:
            raise ModelUnavailableError("Config and manifest checkpoint hashes differ")
        if self.config["class_names"] != self.manifest["classes"]:
            raise ModelUnavailableError("Config and manifest class mappings differ")
        if self.config["preprocessing_variant"] != "P3" or self.config["augmentation"] is not False:
            raise ModelUnavailableError("Eggplant v1 preprocessing lock is invalid")

    def _validate_model(self) -> None:
        if list(self.model.input_shape[1:]) != [224, 224, 3]:
            raise ModelUnavailableError("Eggplant v1 model input shape is invalid")
        if int(self.model.output_shape[-1]) != len(self.config["class_names"]):
            raise ModelUnavailableError("Eggplant v1 model output shape is invalid")

    def _prepare(self, image: ValidatedImage) -> np.ndarray:
        try:
            with Image.open(BytesIO(image.content)) as decoded:
                decoded.load()
                rgb = decoded.convert("RGB")
            processed = self._preprocess(rgb, "P3", self.preprocessing_config)
        except (UnidentifiedImageError, OSError, ValueError) as error:
            raise InferenceError("Validated image could not be preprocessed") from error
        array = np.asarray(processed, dtype=np.float32)
        if array.shape != (224, 224, 3) or not np.isfinite(array).all():
            raise InferenceError("Preprocessing output is invalid")
        return array

    def predict_many(self, images: Sequence[ValidatedImage]) -> AggregatePrediction:
        if not 1 <= len(images) <= 3:
            raise InferenceError("Inference requires one to three images")
        batch = np.stack([self._prepare(image) for image in images])
        try:
            with self._inference_lock:
                output = self.model(batch, training=False)
            probabilities = np.asarray(output, dtype=np.float64)
        except Exception as error:
            raise InferenceError("Model inference failed") from error
        if probabilities.shape != (len(images), len(self.class_names)):
            raise InferenceError("Model returned an invalid probability shape")
        if not np.isfinite(probabilities).all() or not np.allclose(
            probabilities.sum(axis=1), 1.0, atol=1e-5
        ):
            raise InferenceError("Model returned invalid probabilities")
        image_predictions = tuple(self._to_prediction(row) for row in probabilities)
        averaged = probabilities.mean(axis=0)
        aggregate = self._to_prediction(averaged)
        return AggregatePrediction(
            class_name=aggregate.class_name,
            class_index=aggregate.class_index,
            confidence=aggregate.confidence,
            probabilities=aggregate.probabilities,
            image_predictions=image_predictions,
        )

    def predict(self, image: ValidatedImage) -> ImagePrediction:
        aggregate = self.predict_many([image])
        return aggregate.image_predictions[0]

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

    def analyze(self, images: Sequence[ValidatedImage]) -> AnalyzeResponse:
        prediction = self.predict_many(images)
        disease = get_disease_record("eggplant", prediction.class_name)
        return AnalyzeResponse(
            image_count=len(images),
            plant=PlantPrediction(
                code=str(disease["plant_code"]),
                name_th=str(disease["plant_name_th"]),
                name_en=str(disease["plant_name_en"]),
                confidence=1.0,
            ),
            disease=DiseasePrediction(
                code=str(disease["disease_code"]),
                name_th=str(disease["disease_name_th"]),
                name_en=str(disease["disease_name_en"]),
                confidence=prediction.confidence,
            ),
            symptoms=list(disease["symptoms"]),
            care=list(disease["care"]),
            prevention=list(disease["prevention"]),
        )


@lru_cache(maxsize=1)
def get_eggplant_model_service() -> EggplantModelService:
    manifest_path = Path(settings.eggplant_model_manifest)
    if not manifest_path.is_absolute():
        manifest_path = (Path(__file__).resolve().parents[2] / manifest_path).resolve()
    return EggplantModelService(manifest_path)
