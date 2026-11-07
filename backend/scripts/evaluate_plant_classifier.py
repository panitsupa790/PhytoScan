from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import tensorflow as tf


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.image_service import ValidatedImage  # noqa: E402
from app.services.model_registry import get_classifier_config  # noqa: E402
from app.services.plant_classifier_service import (  # noqa: E402
    PlantClassifierService,
)


DEFAULT_VALIDATION = Path(
    r"\\wsl.localhost\Ubuntu\home\mind_hp\phytoscan\phytoscan\models"
    r"\plant_classifier_v1\valid_split.csv"
)
DEFAULT_TEST = Path(
    r"\\wsl.localhost\Ubuntu\home\mind_hp\phytoscan\phytoscan\models"
    r"\plant_classifier_v1\test_split.csv"
)
CONFIG_PATH = BACKEND_ROOT / "app" / "data" / "plant_classifier_evaluation.json"
CORRECTIVE_CONFIG_PATH = (
    BACKEND_ROOT / "app" / "data" / "plant_classifier_evaluation_corrective.json"
)
CORRECTIVE_RECEIPT_PATH = (
    BACKEND_ROOT / "app" / "data" / "plant_classifier_corrective_test_receipt.json"
)
REPORT_DIR = BACKEND_ROOT / "evaluation"
CORRECTIVE_VALIDATION_JSON = REPORT_DIR / "plant_classifier_validation_corrective_report.json"
CORRECTIVE_VALIDATION_MD = REPORT_DIR / "plant_classifier_validation_corrective_report.md"
CORRECTIVE_VALIDATION_ROWS = (
    REPORT_DIR / "plant_classifier_validation_corrective_predictions.csv"
)
CORRECTIVE_TEST_JSON = REPORT_DIR / "plant_classifier_test_corrective_report.json"
CORRECTIVE_TEST_MD = REPORT_DIR / "plant_classifier_test_corrective_report.md"
CORRECTIVE_TEST_ROWS = REPORT_DIR / "plant_classifier_test_corrective_predictions.csv"
CANDIDATE_CONFIG_PATH = (
    BACKEND_ROOT / "app" / "data" / "plant_classifier_threshold.hybrid_candidate.json"
)
CANDIDATE_REPORT_DIR = REPORT_DIR / "hybrid_candidate_v1"
CANDIDATE_MANIFEST_PATH = (
    BACKEND_ROOT / "app" / "data" / "model_manifest.hybrid_candidate.json"
)
CANDIDATE_TEST_DIR = CANDIDATE_REPORT_DIR / "final_test_20261101"
CANDIDATE_RECEIPT_PATH = (
    BACKEND_ROOT
    / "app"
    / "data"
    / "plant_classifier_hybrid_candidate_test_receipt.json"
)
DEFAULT_REGRESSION_PREDICTIONS = Path(
    r"\\wsl.localhost\Ubuntu\home\mind_hp\phytoscan\phytoscan\models"
    r"\plant_classifier_mobilenetv2\comparison_reports"
    r"\20261101_035921_262354\test_predictions.csv"
)
REQUIRED_COLUMNS = {"path", "plant", "label", "split", "group_id"}

METRIC_DEFINITIONS = {
    "coverage": "accepted_samples / total_samples",
    "accepted_accuracy": "accepted_correct / accepted_samples (N/A when accepted_samples is 0)",
    "false_acceptance_rate_among_incorrect_predictions": "accepted_incorrect / total_incorrect_predictions (N/A when total_incorrect_predictions is 0)",
    "accepted_error_rate": "accepted_incorrect / accepted_samples (N/A when accepted_samples is 0)",
    "correct_rejections": "rejected_incorrect_predictions; percentage denominator is total_incorrect_predictions",
    "wrongful_rejections": "rejected_correct_predictions; percentage denominator is total_correct_predictions",
    "per_class_basis": "true plant label",
}

SELECTION_CRITERIA = [
    "Candidates are 0.0, nextafter(each observed validation value, +inf), and 1.0 in inference float precision.",
    "Accept when confidence >= MIN_CONFIDENCE and margin >= MIN_MARGIN.",
    "Require at least one accepted sample for every true plant class; reject-all is forbidden.",
    "Minimize accepted errors (therefore prefer zero), then maximize coverage.",
    "Break remaining ties by lowest MIN_CONFIDENCE, then lowest MIN_MARGIN.",
    "Test data is not used to construct candidates, select, or adjust thresholds.",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_image_path(raw_path: str) -> Path:
    normalized = raw_path.strip().replace("\\", "/")
    if normalized.startswith("/mnt/") and len(normalized) > 6:
        drive = normalized[5].upper()
        return Path(f"{drive}:/{normalized[7:]}")
    return Path(raw_path)


def load_manifest(path: Path, expected_split: str, class_order: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if set(reader.fieldnames or ()) != REQUIRED_COLUMNS:
            raise ValueError(f"Unexpected manifest columns: {reader.fieldnames}")
        rows = list(reader)
    if not rows:
        raise ValueError("Manifest is empty")
    seen_paths: set[str] = set()
    for row in rows:
        if row["split"].strip().lower() not in {expected_split, "validation" if expected_split == "valid" else expected_split}:
            raise ValueError(f"Unexpected split value: {row['split']}")
        plant = row["plant"].strip()
        label = int(row["label"])
        if plant not in class_order or label != class_order.index(plant):
            raise ValueError(f"Class mapping mismatch for {plant}/{label}")
        image_path = str(resolve_image_path(row["path"]))
        if image_path in seen_paths:
            raise ValueError(f"Duplicate image path: {row['path']}")
        seen_paths.add(image_path)
        if not resolve_image_path(row["path"]).is_file():
            raise FileNotFoundError(row["path"])
    return rows


def infer(
    rows: list[dict[str, str]], service: PlantClassifierService, batch_size: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    labels = np.asarray([int(row["label"]) for row in rows], dtype=np.int64)
    all_probabilities: list[np.ndarray] = []
    for start in range(0, len(rows), batch_size):
        images = []
        for row in rows[start : start + batch_size]:
            path = resolve_image_path(row["path"])
            content = path.read_bytes()
            images.append(
                ValidatedImage(
                    filename=path.name,
                    content_type="image/unknown",
                    image_format="UNKNOWN",
                    size_bytes=len(content),
                    width=0,
                    height=0,
                    content=content,
                )
            )
        batch = np.stack([service._prepare(image) for image in images])
        output = np.asarray(service.model(batch, training=False), dtype=np.float32)
        if output.shape != (len(images), len(service.class_names)):
            raise ValueError("Classifier returned an invalid output shape")
        if not np.isfinite(output).all() or not np.allclose(output.sum(axis=1), 1.0, atol=1e-5):
            raise ValueError("Classifier returned NaN, Inf, or invalid probabilities")
        all_probabilities.append(output)
        print(f"inference {min(start + batch_size, len(rows))}/{len(rows)}", flush=True)
    probabilities = np.concatenate(all_probabilities, axis=0)
    predictions = probabilities.argmax(axis=1)
    ordered = np.sort(probabilities, axis=1)
    confidence = ordered[:, -1].astype(np.float32)
    margin = (ordered[:, -1] - ordered[:, -2]).astype(np.float32)
    return labels, predictions, np.column_stack((confidence, margin)).astype(np.float32)


def observed_candidates(values: np.ndarray) -> np.ndarray:
    finite = values[np.isfinite(values)].astype(np.float32)
    candidates = np.concatenate(
        (
            np.asarray([0.0, 1.0], dtype=np.float32),
            np.nextafter(finite, np.float32(np.inf), dtype=np.float32),
        )
    )
    candidates = candidates[np.isfinite(candidates) & (candidates >= 0.0) & (candidates <= 1.0)]
    return np.unique(candidates)


def select_thresholds(
    labels: np.ndarray,
    predictions: np.ndarray,
    confidence: np.ndarray,
    margin: np.ndarray,
    class_count: int,
) -> tuple[np.float32, np.float32]:
    confidence_candidates = observed_candidates(confidence)
    margin_candidates = observed_candidates(margin)
    correct = predictions == labels
    best_key: tuple[int, int, float, float] | None = None
    best_pair: tuple[np.float32, np.float32] | None = None
    for min_confidence in confidence_candidates:
        confidence_ok = confidence >= min_confidence
        eligible_margins = np.sort(margin[confidence_ok])
        accepted_counts = len(eligible_margins) - np.searchsorted(
            eligible_margins, margin_candidates, side="left"
        )
        error_margins = np.sort(margin[confidence_ok & ~correct])
        error_counts = len(error_margins) - np.searchsorted(
            error_margins, margin_candidates, side="left"
        )
        valid = np.ones(len(margin_candidates), dtype=bool)
        for index in range(class_count):
            class_margins = np.sort(margin[confidence_ok & (labels == index)])
            class_counts = len(class_margins) - np.searchsorted(
                class_margins, margin_candidates, side="left"
            )
            valid &= class_counts > 0
        valid_indexes = np.flatnonzero(valid)
        if not len(valid_indexes):
            continue
        minimum_errors = error_counts[valid_indexes].min()
        candidate_indexes = valid_indexes[error_counts[valid_indexes] == minimum_errors]
        maximum_accepted = accepted_counts[candidate_indexes].max()
        candidate_indexes = candidate_indexes[
            accepted_counts[candidate_indexes] == maximum_accepted
        ]
        margin_index = int(candidate_indexes[0])
        min_margin = margin_candidates[margin_index]
        key = (
            int(error_counts[margin_index]),
            -int(accepted_counts[margin_index]),
            float(min_confidence),
            float(min_margin),
        )
        if best_key is None or key < best_key:
            best_key = key
            best_pair = (min_confidence, min_margin)
    if best_pair is None:
        raise ValueError("No threshold pair accepts at least one sample in every class")
    return best_pair


def ratio(numerator: int, denominator: int) -> dict[str, int | float | None]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "percentage": None if denominator == 0 else (100.0 * numerator / denominator),
    }


def metrics_for_mask(correct: np.ndarray, accepted: np.ndarray) -> dict[str, Any]:
    total = len(correct)
    accepted_count = int(accepted.sum())
    accepted_correct = int((accepted & correct).sum())
    accepted_incorrect = int((accepted & ~correct).sum())
    total_correct = int(correct.sum())
    total_incorrect = int((~correct).sum())
    rejected_incorrect = int((~accepted & ~correct).sum())
    rejected_correct = int((~accepted & correct).sum())
    return {
        "sample_counts": {
            "total": total,
            "correct_predictions": total_correct,
            "incorrect_predictions": total_incorrect,
            "accepted": accepted_count,
            "accepted_correct": accepted_correct,
            "accepted_incorrect": accepted_incorrect,
            "rejected": total - accepted_count,
        },
        "coverage": ratio(accepted_count, total),
        "accepted_accuracy": ratio(accepted_correct, accepted_count),
        "false_acceptance_rate_among_incorrect_predictions": ratio(accepted_incorrect, total_incorrect),
        "accepted_error_rate": ratio(accepted_incorrect, accepted_count),
        "correct_rejections": ratio(rejected_incorrect, total_incorrect),
        "wrongful_rejections": ratio(rejected_correct, total_correct),
    }


def raw_classification_metrics(
    labels: np.ndarray,
    predictions: np.ndarray,
    class_order: tuple[str, ...],
) -> tuple[dict[str, Any], np.ndarray]:
    class_count = len(class_order)
    confusion = np.zeros((class_count, class_count), dtype=np.int64)
    np.add.at(confusion, (labels, predictions), 1)
    per_class: dict[str, Any] = {}
    precisions: list[float] = []
    recalls: list[float] = []
    f1_scores: list[float] = []
    for index, class_name in enumerate(class_order):
        true_positive = int(confusion[index, index])
        false_positive = int(confusion[:, index].sum() - true_positive)
        false_negative = int(confusion[index, :].sum() - true_positive)
        support = int(confusion[index, :].sum())
        predicted_count = int(confusion[:, index].sum())
        precision = (
            0.0
            if true_positive + false_positive == 0
            else true_positive / (true_positive + false_positive)
        )
        recall = (
            0.0
            if true_positive + false_negative == 0
            else true_positive / (true_positive + false_negative)
        )
        f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
        precisions.append(precision)
        recalls.append(recall)
        f1_scores.append(f1)
        per_class[class_name] = {
            "support": support,
            "predicted_count": predicted_count,
            "correct": true_positive,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    correct = int((labels == predictions).sum())
    total = len(labels)
    return (
        {
            "total": total,
            "correct": correct,
            "incorrect": total - correct,
            "accuracy": correct / total,
            "macro_precision": float(np.mean(precisions)),
            "macro_recall": float(np.mean(recalls)),
            "macro_f1": float(np.mean(f1_scores)),
            "minimum_per_class_recall": float(np.min(recalls)),
            "per_true_class": per_class,
        },
        confusion,
    )


def write_confusion_matrix_csv(
    path: Path, confusion: np.ndarray, class_order: tuple[str, ...]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as destination:
        writer = csv.writer(destination)
        writer.writerow(["true\\predicted", *class_order])
        for class_name, row in zip(class_order, confusion):
            writer.writerow([class_name, *(int(value) for value in row)])


def build_report(
    split: str,
    rows: list[dict[str, str]],
    labels: np.ndarray,
    predictions: np.ndarray,
    scores: np.ndarray,
    thresholds: tuple[float, float],
    class_order: tuple[str, ...],
    validation_error_count: int,
) -> dict[str, Any]:
    confidence, margin = scores[:, 0], scores[:, 1]
    accepted = (confidence >= thresholds[0]) & (margin >= thresholds[1])
    correct = predictions == labels
    per_class = {}
    for index, plant in enumerate(class_order):
        mask = labels == index
        per_class[plant] = metrics_for_mask(correct[mask], accepted[mask])
    return {
        "split": split,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "thresholds": {"min_confidence": thresholds[0], "min_margin": thresholds[1]},
        "dataset_counts": {"total": len(rows), "per_true_plant": dict(Counter(row["plant"] for row in rows))},
        "metrics": {"overall": metrics_for_mask(correct, accepted), "per_true_plant": per_class},
        "metric_definitions": METRIC_DEFINITIONS,
        "limitations": [
            "No unsupported/OOD dataset was evaluated; thresholds only filter low-confidence predictions among supported plants.",
            f"This evaluation observed only {validation_error_count} incorrect validation predictions (the supplied prior expectation was 7), so zero accepted validation errors cannot guarantee zero errors in production.",
            "This is not an external test set and may overlap with data used by one or more disease classifiers.",
        ],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ensure_absent(paths: Iterable[Path], purpose: str) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise FileExistsError(
            f"{purpose} artifacts already exist; refusing to repeat or overwrite: "
            + ", ".join(existing)
        )


def write_predictions_csv(
    path: Path,
    rows: list[dict[str, str]],
    labels: np.ndarray,
    predictions: np.ndarray,
    scores: np.ndarray,
    thresholds: tuple[float, float],
    class_order: tuple[str, ...],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    confidence, margin = scores[:, 0], scores[:, 1]
    accepted = (confidence >= thresholds[0]) & (margin >= thresholds[1])
    with path.open("x", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(
            destination,
            fieldnames=[
                "row_index",
                "path",
                "group_id",
                "true_label",
                "true_plant",
                "predicted_label",
                "predicted_plant",
                "confidence",
                "margin",
                "correct",
                "accepted",
            ],
        )
        writer.writeheader()
        for index, row in enumerate(rows):
            predicted_label = int(predictions[index])
            writer.writerow(
                {
                    "row_index": index,
                    "path": row["path"],
                    "group_id": row["group_id"],
                    "true_label": int(labels[index]),
                    "true_plant": row["plant"],
                    "predicted_label": predicted_label,
                    "predicted_plant": class_order[predicted_label],
                    "confidence": repr(float(confidence[index])),
                    "margin": repr(float(margin[index])),
                    "correct": bool(predictions[index] == labels[index]),
                    "accepted": bool(accepted[index]),
                }
            )


def format_percentage(metric: dict[str, Any]) -> str:
    value = metric["percentage"]
    display = "N/A" if value is None else f"{value:.4f}%"
    return f"{metric['numerator']}/{metric['denominator']} ({display})"


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    overall = report["metrics"]["overall"]
    lines = [
        f"# Plant Classifier {report['split'].title()} Evaluation",
        "",
        f"Thresholds: confidence >= `{report['thresholds']['min_confidence']!r}`, margin >= `{report['thresholds']['min_margin']!r}`.",
        "",
        "| Scope | Coverage | Accepted accuracy | FAR among incorrect | Correct rejections | Wrongful rejections |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    scopes: Iterable[tuple[str, dict[str, Any]]] = [("Overall", overall), *report["metrics"]["per_true_plant"].items()]
    for name, metrics in scopes:
        lines.append(
            f"| {name} | {format_percentage(metrics['coverage'])} | "
            f"{format_percentage(metrics['accepted_accuracy'])} | "
            f"{format_percentage(metrics['false_acceptance_rate_among_incorrect_predictions'])} | "
            f"{format_percentage(metrics['correct_rejections'])} | "
            f"{format_percentage(metrics['wrongful_rejections'])} |"
        )
    lines.extend(["", "## Limitations", ""] + [f"- {item}" for item in report["limitations"]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def frozen_config(
    manifest_path: Path,
    rows: list[dict[str, str]],
    thresholds: tuple[float, float],
    report: dict[str, Any],
    *,
    status: str = "frozen_before_test",
    reason: str | None = None,
) -> dict[str, Any]:
    model = get_classifier_config()
    return {
        "schema_version": 1,
        "status": status,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "thresholds": {"min_confidence": thresholds[0], "min_margin": thresholds[1]},
        "selection_criteria": SELECTION_CRITERIA,
        "metric_definitions": METRIC_DEFINITIONS,
        "model": {
            "model_version": model.model_version,
            "sha256": model.sha256,
            "class_order": list(model.class_order),
            "input_shape": list(model.input_shape),
            "preprocessing": model.preprocessing,
            "input_contract": {
                "decoder": model.decoder,
                "resize_method": model.resize_method,
                "channels": 3,
                "expand_animations": False,
                "target_size": list(model.input_shape[:2]),
                "dtype": "float32",
                "pixel_range": [0, 255],
                "external_normalization": False,
                "preprocessing": model.preprocessing,
            },
            "inference_float_precision": "float32",
        },
        "validation_dataset": {
            "manifest": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "total": len(rows),
            "per_true_plant": report["dataset_counts"]["per_true_plant"],
        },
        "test_protocol": {
            "manifest": "/home/mind_hp/phytoscan/phytoscan/models/plant_classifier_v1/test_split.csv",
            "purpose": "evaluation_only",
            "threshold_adjustment_permitted": False,
        },
        "limitations": report["limitations"],
    }


def _corrective_config() -> dict[str, Any]:
    if not CORRECTIVE_CONFIG_PATH.is_file():
        raise FileNotFoundError("Corrective frozen validation configuration is required")
    document = json.loads(CORRECTIVE_CONFIG_PATH.read_text(encoding="utf-8"))
    config = get_classifier_config()
    expected_contract = {
        "decoder": config.decoder,
        "resize_method": config.resize_method,
        "channels": 3,
        "expand_animations": False,
        "target_size": list(config.input_shape[:2]),
        "dtype": "float32",
        "pixel_range": [0, 255],
        "external_normalization": False,
        "preprocessing": config.preprocessing,
    }
    if document.get("status") != "corrective_frozen_before_test":
        raise ValueError("Corrective evaluation configuration is not frozen before Test")
    if document["model"]["sha256"] != config.sha256:
        raise ValueError("Corrective configuration does not match the classifier SHA-256")
    if tuple(document["model"]["class_order"]) != config.class_order:
        raise ValueError("Corrective configuration does not match classifier class order")
    if document["model"].get("input_contract") != expected_contract:
        raise ValueError("Corrective configuration does not match runtime preprocessing")
    return document


def run_corrective_validation(args: argparse.Namespace) -> None:
    artifacts = (
        CORRECTIVE_CONFIG_PATH,
        CORRECTIVE_VALIDATION_JSON,
        CORRECTIVE_VALIDATION_MD,
        CORRECTIVE_VALIDATION_ROWS,
        CORRECTIVE_TEST_JSON,
        CORRECTIVE_TEST_MD,
        CORRECTIVE_TEST_ROWS,
        CORRECTIVE_RECEIPT_PATH,
    )
    ensure_absent(artifacts, "Corrective evaluation")
    config = get_classifier_config()
    rows = load_manifest(args.manifest, "valid", config.class_order)
    service = PlantClassifierService(config)
    labels, predictions, scores = infer(rows, service, args.batch_size)
    min_confidence, min_margin = select_thresholds(
        labels, predictions, scores[:, 0], scores[:, 1], len(config.class_order)
    )
    thresholds = (float(min_confidence), float(min_margin))
    validation_error_count = int((predictions != labels).sum())
    report = build_report(
        "corrective validation",
        rows,
        labels,
        predictions,
        scores,
        thresholds,
        config.class_order,
        validation_error_count,
    )
    report["evaluation_protocol"] = {
        "phase": "1.2 Threshold Recalibration & Corrective Evaluation",
        "preprocessing": "TensorFlow decode_image RGB and bilinear resize",
        "threshold_selection_source": "validation_only",
        "test_used_for_selection": False,
        "selection_criteria": SELECTION_CRITERIA,
        "reason": "Correct preprocessing mismatch found by the Phase 1 parity audit",
    }
    write_json(CORRECTIVE_VALIDATION_JSON, report)
    write_markdown(CORRECTIVE_VALIDATION_MD, report)
    write_predictions_csv(
        CORRECTIVE_VALIDATION_ROWS,
        rows,
        labels,
        predictions,
        scores,
        thresholds,
        config.class_order,
    )
    document = frozen_config(
        args.manifest,
        rows,
        thresholds,
        report,
        status="corrective_frozen_before_test",
        reason="Recalibrated after replacing Pillow preprocessing with the Notebook-compatible TensorFlow input contract",
    )
    document["artifacts"] = {
        "validation_report": str(CORRECTIVE_VALIDATION_JSON.relative_to(BACKEND_ROOT)),
        "validation_predictions": str(CORRECTIVE_VALIDATION_ROWS.relative_to(BACKEND_ROOT)),
    }
    write_json(CORRECTIVE_CONFIG_PATH, document)
    print(
        json.dumps(
            {
                "thresholds": report["thresholds"],
                "metrics": report["metrics"]["overall"],
                "frozen_config": str(CORRECTIVE_CONFIG_PATH),
                "frozen_config_sha256": sha256_file(CORRECTIVE_CONFIG_PATH),
            },
            indent=2,
        )
    )


def run_corrective_test(args: argparse.Namespace) -> None:
    ensure_absent(
        (
            CORRECTIVE_TEST_JSON,
            CORRECTIVE_TEST_MD,
            CORRECTIVE_TEST_ROWS,
            CORRECTIVE_RECEIPT_PATH,
        ),
        "Corrective Test evaluation",
    )
    document = _corrective_config()
    config_sha256 = sha256_file(CORRECTIVE_CONFIG_PATH)
    thresholds = (
        float(document["thresholds"]["min_confidence"]),
        float(document["thresholds"]["min_margin"]),
    )
    rows = load_manifest(args.manifest, "test", get_classifier_config().class_order)
    validation_rows = load_manifest(
        args.validation_manifest, "valid", get_classifier_config().class_order
    )
    if sha256_file(args.validation_manifest) != document["validation_dataset"]["manifest_sha256"]:
        raise ValueError("Validation manifest differs from the manifest used to freeze thresholds")
    if {row["path"] for row in rows} & {row["path"] for row in validation_rows}:
        raise ValueError("Validation/test path leakage detected")
    if {row["group_id"] for row in rows} & {row["group_id"] for row in validation_rows}:
        raise ValueError("Validation/test group leakage detected")
    service = PlantClassifierService(get_classifier_config())
    labels, predictions, scores = infer(rows, service, args.batch_size)
    validation_report = json.loads(CORRECTIVE_VALIDATION_JSON.read_text(encoding="utf-8"))
    validation_error_count = validation_report["metrics"]["overall"]["sample_counts"][
        "incorrect_predictions"
    ]
    report = build_report(
        "corrective test",
        rows,
        labels,
        predictions,
        scores,
        thresholds,
        get_classifier_config().class_order,
        validation_error_count,
    )
    report["evaluation_protocol"] = {
        "phase": "1.2 Corrective Re-evaluation",
        "reason": "The historical Test used Pillow preprocessing; this run uses the frozen Notebook-compatible TensorFlow contract",
        "frozen_config_sha256": config_sha256,
        "threshold_selection_performed": False,
        "threshold_adjustment_permitted": False,
        "test_used_for_selection": False,
    }
    report["integrity_checks"] = {
        "path_leakage": 0,
        "group_id_leakage": 0,
        "validation_manifest_sha256_matches_frozen_config": True,
    }
    write_json(CORRECTIVE_TEST_JSON, report)
    write_markdown(CORRECTIVE_TEST_MD, report)
    write_predictions_csv(
        CORRECTIVE_TEST_ROWS,
        rows,
        labels,
        predictions,
        scores,
        thresholds,
        get_classifier_config().class_order,
    )
    receipt = {
        "schema_version": 1,
        "status": "corrective_test_completed",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "reason": "Corrective Test re-evaluation after preprocessing parity fix",
        "frozen_config": str(CORRECTIVE_CONFIG_PATH.relative_to(BACKEND_ROOT)),
        "frozen_config_sha256": config_sha256,
        "thresholds": document["thresholds"],
        "threshold_selection_performed_on_test": False,
        "threshold_adjustment_permitted_from_test": False,
        "artifacts": {
            "test_report": {
                "path": str(CORRECTIVE_TEST_JSON.relative_to(BACKEND_ROOT)),
                "sha256": sha256_file(CORRECTIVE_TEST_JSON),
            },
            "test_predictions": {
                "path": str(CORRECTIVE_TEST_ROWS.relative_to(BACKEND_ROOT)),
                "sha256": sha256_file(CORRECTIVE_TEST_ROWS),
            },
        },
    }
    write_json(CORRECTIVE_RECEIPT_PATH, receipt)
    print(
        json.dumps(
            {
                "thresholds": report["thresholds"],
                "metrics": report["metrics"]["overall"],
                "receipt": str(CORRECTIVE_RECEIPT_PATH),
            },
            indent=2,
        )
    )


def run_validation(args: argparse.Namespace) -> None:
    config = get_classifier_config()
    rows = load_manifest(args.manifest, "valid", config.class_order)
    service = PlantClassifierService(config)
    labels, predictions, scores = infer(rows, service, args.batch_size)
    min_confidence, min_margin = select_thresholds(
        labels, predictions, scores[:, 0], scores[:, 1], len(config.class_order)
    )
    thresholds = (float(min_confidence), float(min_margin))
    validation_error_count = int((predictions != labels).sum())
    report = build_report(
        "validation",
        rows,
        labels,
        predictions,
        scores,
        thresholds,
        config.class_order,
        validation_error_count,
    )
    write_json(REPORT_DIR / "plant_classifier_validation_report.json", report)
    write_markdown(REPORT_DIR / "plant_classifier_validation_report.md", report)
    write_json(CONFIG_PATH, frozen_config(args.manifest, rows, thresholds, report))
    print(json.dumps({"thresholds": report["thresholds"], "metrics": report["metrics"]["overall"]}, indent=2))


def run_candidate_validation(args: argparse.Namespace) -> None:
    output_dir = args.output_dir.resolve()
    config_path = args.config_path.resolve()
    report_path = output_dir / "plant_classifier_validation_report.json"
    markdown_path = output_dir / "plant_classifier_validation_report.md"
    predictions_path = output_dir / "plant_classifier_validation_predictions.csv"
    ensure_absent(
        (config_path, report_path, markdown_path, predictions_path),
        "hybrid candidate validation",
    )
    config = get_classifier_config()
    if config.architecture != "MobileNetV2":
        raise ValueError("Hybrid candidate validation requires MobileNetV2")
    rows = load_manifest(args.manifest, "valid", config.class_order)
    service = PlantClassifierService(config)
    labels, predictions, scores = infer(rows, service, args.batch_size)
    confidence, margin = scores[:, 0], scores[:, 1]
    min_confidence, min_margin = select_thresholds(
        labels,
        predictions,
        confidence,
        margin,
        len(config.class_order),
    )
    thresholds = (float(min_confidence), float(min_margin))
    validation_error_count = int((predictions != labels).sum())
    report = build_report(
        "hybrid_candidate_validation",
        rows,
        labels,
        predictions,
        scores,
        thresholds,
        config.class_order,
        validation_error_count,
    )
    report["purpose"] = "candidate threshold selection from validation only"
    report["test_data_opened"] = False
    report["activation_status"] = "candidate_staging_not_active"
    write_json(report_path, report)
    write_markdown(markdown_path, report)
    write_predictions_csv(
        predictions_path,
        rows,
        labels,
        predictions,
        scores,
        thresholds,
        config.class_order,
    )
    document = frozen_config(
        args.manifest,
        rows,
        thresholds,
        report,
        status="candidate_frozen_before_test",
        reason=(
            "MobileNetV2 hybrid candidate recalibration on the V1 validation "
            "manifest only; Test remains unopened by this workflow"
        ),
    )
    document["manifest_id"] = "phytoscan-hybrid-candidate-v1"
    document["activation_status"] = "candidate_staging_not_active"
    document["test_evaluation_status"] = "not_run"
    document["validation_artifacts"] = {
        "report": {
            "path": str(report_path.relative_to(BACKEND_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(report_path),
        },
        "predictions": {
            "path": str(predictions_path.relative_to(BACKEND_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(predictions_path),
        },
    }
    write_json(config_path, document)
    print(
        json.dumps(
            {
                "thresholds": report["thresholds"],
                "metrics": report["metrics"]["overall"],
                "config_path": str(config_path),
                "config_sha256": sha256_file(config_path),
                "test_data_opened": False,
            },
            indent=2,
        )
    )


def _candidate_frozen_config(
    config_path: Path,
    validation_manifest: Path,
) -> dict[str, Any]:
    document = json.loads(config_path.read_text(encoding="utf-8"))
    model = get_classifier_config()
    expected_contract = {
        "decoder": model.decoder,
        "resize_method": model.resize_method,
        "channels": 3,
        "expand_animations": False,
        "target_size": list(model.input_shape[:2]),
        "dtype": "float32",
        "pixel_range": [0, 255],
        "external_normalization": False,
        "preprocessing": model.preprocessing,
    }
    if document.get("status") != "candidate_frozen_before_test":
        raise ValueError("Candidate threshold configuration is not frozen before Test")
    if document.get("test_evaluation_status") != "not_run":
        raise ValueError("Candidate Test has already been recorded")
    if document["model"]["sha256"] != model.sha256:
        raise ValueError("Frozen threshold model SHA-256 differs from runtime")
    if tuple(document["model"]["class_order"]) != model.class_order:
        raise ValueError("Frozen threshold class order differs from runtime")
    if document["model"].get("input_contract") != expected_contract:
        raise ValueError("Frozen threshold preprocessing differs from runtime")
    if sha256_file(validation_manifest) != document["validation_dataset"]["manifest_sha256"]:
        raise ValueError("Validation manifest differs from frozen threshold config")
    return document


def _verify_candidate_bundle_hashes(manifest_path: Path) -> dict[str, str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "candidate_staging_not_active":
        raise ValueError("Candidate manifest activation state is invalid")
    if manifest.get("activation_requires_explicit_approval") is not True:
        raise ValueError("Candidate manifest lacks explicit activation guard")
    entries = {
        "plant_classifier": manifest["plant_classifier"],
        **manifest["models"],
    }
    verified: dict[str, str] = {}
    app_root = BACKEND_ROOT / "app"
    for name, entry in entries.items():
        model_path = (app_root / str(entry["model_path"])).resolve()
        if app_root not in model_path.parents or not model_path.is_file():
            raise ValueError(f"Invalid candidate model path for {name}")
        actual_sha = sha256_file(model_path)
        if actual_sha != str(entry["sha256"]).lower():
            raise ValueError(f"Candidate model SHA-256 mismatch for {name}")
        verified[name] = actual_sha
    return verified


def _compare_regression_predictions(
    path: Path,
    rows: list[dict[str, str]],
    labels: np.ndarray,
    predictions: np.ndarray,
    class_order: tuple[str, ...],
) -> dict[str, Any]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        historical_rows = list(csv.DictReader(source))
    if len(historical_rows) != len(rows):
        raise ValueError("Historical regression predictions have a different row count")
    historical_by_path = {row["path"]: row for row in historical_rows}
    if len(historical_by_path) != len(historical_rows):
        raise ValueError("Historical regression predictions contain duplicate paths")
    historical_predictions: list[int] = []
    for row, label in zip(rows, labels):
        historical = historical_by_path.get(row["path"])
        if historical is None:
            raise ValueError("Historical regression predictions use a different Test set")
        if int(historical["label"]) != int(label) or historical["plant"] != row["plant"]:
            raise ValueError("Historical regression label mapping differs from candidate Test")
        historical_predictions.append(int(historical["pred_MobileNetV2"]))
    historical_array = np.asarray(historical_predictions, dtype=np.int64)
    historical_metrics, _ = raw_classification_metrics(
        labels, historical_array, class_order
    )
    changed = np.flatnonzero(historical_array != predictions)
    return {
        "source": str(path),
        "source_sha256": sha256_file(path),
        "row_count": len(historical_rows),
        "same_test_paths_and_labels": True,
        "historical_mobile_metrics": historical_metrics,
        "prediction_disagreement_count": int(len(changed)),
        "prediction_disagreement_row_indexes": [int(index) for index in changed],
        "used_for_threshold_or_model_selection": False,
    }


def _write_candidate_test_markdown(path: Path, report: dict[str, Any]) -> None:
    raw = report["raw_classification_metrics"]
    thresholded = report["metrics"]["overall"]
    lines = [
        "# Hybrid Candidate Final Plant Classifier Test",
        "",
        "Test purpose: evaluation only after threshold freeze; no threshold or model selection was performed.",
        "",
        f"- Raw accuracy: `{raw['correct']}/{raw['total']}` ({raw['accuracy'] * 100:.4f}%)",
        f"- Macro precision: `{raw['macro_precision'] * 100:.4f}%`",
        f"- Macro recall: `{raw['macro_recall'] * 100:.4f}%`",
        f"- Macro F1: `{raw['macro_f1'] * 100:.4f}%`",
        f"- Minimum per-class recall: `{raw['minimum_per_class_recall'] * 100:.4f}%`",
        f"- Frozen thresholds: confidence >= `{report['thresholds']['min_confidence']!r}`, margin >= `{report['thresholds']['min_margin']!r}`",
        "",
        "| Scope | Coverage | Accepted accuracy | Accepted errors | Correct rejections | Wrongful rejections |",
        "|---|---:|---:|---:|---:|---:|",
        f"| Overall | {format_percentage(thresholded['coverage'])} | {format_percentage(thresholded['accepted_accuracy'])} | {thresholded['sample_counts']['accepted_incorrect']} | {format_percentage(thresholded['correct_rejections'])} | {format_percentage(thresholded['wrongful_rejections'])} |",
        "",
        "| True class | Support | Precision | Recall | F1 | Coverage |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for class_name, metrics in raw["per_true_class"].items():
        coverage = report["metrics"]["per_true_plant"][class_name]["coverage"]
        lines.append(
            f"| {class_name} | {metrics['support']} | {metrics['precision'] * 100:.4f}% | "
            f"{metrics['recall'] * 100:.4f}% | {metrics['f1'] * 100:.4f}% | "
            f"{format_percentage(coverage)} |"
        )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Unsupported/OOD detection: NOT VERIFIED.",
            "- This Test set is not an independent external mobile-image test.",
            "- Test results were not used to adjust thresholds or select a model.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_candidate_test(args: argparse.Namespace) -> None:
    output_dir = args.output_dir.resolve()
    report_path = output_dir / "plant_classifier_test_report.json"
    markdown_path = output_dir / "plant_classifier_test_report.md"
    predictions_path = output_dir / "plant_classifier_test_predictions.csv"
    confusion_path = output_dir / "plant_classifier_test_confusion_matrix.csv"
    receipt_path = args.receipt_path.resolve()
    ensure_absent(
        (
            report_path,
            markdown_path,
            predictions_path,
            confusion_path,
            receipt_path,
        ),
        "hybrid candidate final Test",
    )
    config = get_classifier_config()
    if config.architecture != "MobileNetV2":
        raise ValueError("Candidate Test requires the MobileNetV2 plant classifier")
    frozen_config_path = args.frozen_config.resolve()
    frozen = _candidate_frozen_config(
        frozen_config_path,
        args.validation_manifest,
    )
    candidate_manifest_path = args.candidate_manifest.resolve()
    model_hashes = _verify_candidate_bundle_hashes(candidate_manifest_path)
    if model_hashes["plant_classifier"] != config.sha256:
        raise ValueError("Candidate manifest and runtime classifier differ")

    rows = load_manifest(args.manifest, "test", config.class_order)
    validation_rows = load_manifest(
        args.validation_manifest, "valid", config.class_order
    )
    if {row["path"] for row in rows} & {row["path"] for row in validation_rows}:
        raise ValueError("Test and Validation paths overlap")
    if {row["group_id"] for row in rows} & {
        row["group_id"] for row in validation_rows
    }:
        raise ValueError("Test and Validation groups overlap")

    thresholds = (
        float(frozen["thresholds"]["min_confidence"]),
        float(frozen["thresholds"]["min_margin"]),
    )
    service = PlantClassifierService(config)
    labels, predictions, scores = infer(rows, service, args.batch_size)
    validation_error_count = int(
        json.loads(
            (
                CANDIDATE_REPORT_DIR / "plant_classifier_validation_report.json"
            ).read_text(encoding="utf-8")
        )["metrics"]["overall"]["sample_counts"]["incorrect_predictions"]
    )
    report = build_report(
        "hybrid_candidate_final_test",
        rows,
        labels,
        predictions,
        scores,
        thresholds,
        config.class_order,
        validation_error_count,
    )
    raw_metrics, confusion = raw_classification_metrics(
        labels, predictions, config.class_order
    )
    report["raw_classification_metrics"] = raw_metrics
    report["confusion_matrix"] = {
        "orientation": "rows=true_class, columns=predicted_class",
        "class_order": list(config.class_order),
        "values": confusion.tolist(),
    }
    report["protocol"] = {
        "threshold_source": "frozen_validation_config_only",
        "threshold_selection_performed_on_test": False,
        "threshold_adjustment_permitted_from_test": False,
        "model_selection_performed_on_test": False,
        "test_run_count_in_this_candidate_workflow": 1,
    }
    report["artifact_identity"] = {
        "candidate_manifest_sha256": sha256_file(candidate_manifest_path),
        "frozen_threshold_config_sha256": sha256_file(frozen_config_path),
        "test_manifest_sha256": sha256_file(args.manifest),
        "model_sha256": model_hashes,
    }
    report["runtime"] = {
        "tensorflow": tf.__version__,
        "keras": tf.keras.__version__,
        "numpy": np.__version__,
        "inference_float_precision": "float32",
    }
    if args.regression_predictions.is_file():
        report["jupyter_regression"] = _compare_regression_predictions(
            args.regression_predictions,
            rows,
            labels,
            predictions,
            config.class_order,
        )
    else:
        report["jupyter_regression"] = {
            "status": "NOT VERIFIED",
            "reason": "Historical row-level predictions are unavailable",
            "used_for_threshold_or_model_selection": False,
        }

    write_json(report_path, report)
    _write_candidate_test_markdown(markdown_path, report)
    write_predictions_csv(
        predictions_path,
        rows,
        labels,
        predictions,
        scores,
        thresholds,
        config.class_order,
    )
    write_confusion_matrix_csv(confusion_path, confusion, config.class_order)
    receipt = {
        "schema_version": 1,
        "status": "candidate_test_completed",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_id": "phytoscan-hybrid-candidate-v1",
        "candidate_manifest_sha256": sha256_file(candidate_manifest_path),
        "frozen_config_sha256": sha256_file(frozen_config_path),
        "test_manifest_sha256": sha256_file(args.manifest),
        "model_sha256": model_hashes,
        "thresholds": frozen["thresholds"],
        "threshold_selection_performed_on_test": False,
        "threshold_adjustment_permitted_from_test": False,
        "model_selection_performed_on_test": False,
        "metrics": {
            "raw": raw_metrics,
            "threshold_chain": report["metrics"],
        },
        "runtime": report["runtime"],
        "artifacts": {
            "test_report": {
                "path": str(report_path.relative_to(BACKEND_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(report_path),
            },
            "test_predictions": {
                "path": str(predictions_path.relative_to(BACKEND_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(predictions_path),
            },
            "confusion_matrix": {
                "path": str(confusion_path.relative_to(BACKEND_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(confusion_path),
            },
        },
        "unsupported_ood_detection": "NOT VERIFIED",
        "active_manifest_changed": False,
        "deployed": False,
    }
    write_json(receipt_path, receipt)
    print(
        json.dumps(
            {
                "raw_metrics": raw_metrics,
                "threshold_metrics": report["metrics"]["overall"],
                "jupyter_regression": report["jupyter_regression"],
                "receipt": str(receipt_path),
                "receipt_sha256": sha256_file(receipt_path),
            },
            indent=2,
        )
    )


def verify_frozen_validation(args: argparse.Namespace) -> None:
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError("Frozen threshold configuration is required")
    document = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config = get_classifier_config()
    if document.get("status") != "frozen_before_test":
        raise ValueError("Threshold configuration is not frozen")
    if document["model"]["sha256"] != config.sha256:
        raise ValueError("Frozen configuration does not match the classifier")
    thresholds = (
        float(document["thresholds"]["min_confidence"]),
        float(document["thresholds"]["min_margin"]),
    )
    rows = load_manifest(args.manifest, "valid", config.class_order)
    service = PlantClassifierService(config)
    labels, predictions, scores = infer(rows, service, args.batch_size)
    validation_error_count = int((predictions != labels).sum())
    report = build_report(
        "validation_frozen_threshold_after_preprocessing_fix",
        rows,
        labels,
        predictions,
        scores,
        thresholds,
        config.class_order,
        validation_error_count,
    )
    report["verification"] = {
        "thresholds_changed": False,
        "threshold_selection_performed": False,
        "test_opened": False,
        "purpose": "verify previously frozen thresholds with Notebook-compatible preprocessing",
    }
    json_path = REPORT_DIR / "plant_classifier_validation_frozen_threshold_postfix_report.json"
    markdown_path = REPORT_DIR / "plant_classifier_validation_frozen_threshold_postfix_report.md"
    write_json(json_path, report)
    write_markdown(markdown_path, report)
    print(json.dumps({"thresholds": report["thresholds"], "metrics": report["metrics"]["overall"]}, indent=2))


def run_test(args: argparse.Namespace) -> None:
    test_json_path = REPORT_DIR / "plant_classifier_test_report.json"
    test_markdown_path = REPORT_DIR / "plant_classifier_test_report.md"
    if test_json_path.exists() or test_markdown_path.exists():
        raise FileExistsError(
            "Test report already exists; refusing to repeat or overwrite the one-time evaluation"
        )
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError("Frozen validation configuration is required before test evaluation")
    document = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config = get_classifier_config()
    if document.get("status") != "frozen_before_test":
        raise ValueError("Evaluation configuration was not frozen before test")
    if document["model"]["sha256"] != config.sha256 or tuple(document["model"]["class_order"]) != config.class_order:
        raise ValueError("Frozen configuration does not match the classifier")
    thresholds = (
        float(document["thresholds"]["min_confidence"]),
        float(document["thresholds"]["min_margin"]),
    )
    rows = load_manifest(args.manifest, "test", config.class_order)
    validation_rows = load_manifest(args.validation_manifest, "valid", config.class_order)
    if {row["path"] for row in rows} & {row["path"] for row in validation_rows}:
        raise ValueError("Validation/test path leakage detected")
    if {row["group_id"] for row in rows} & {row["group_id"] for row in validation_rows}:
        raise ValueError("Validation/test group leakage detected")
    service = PlantClassifierService(config)
    labels, predictions, scores = infer(rows, service, args.batch_size)
    validation_report = json.loads(
        (REPORT_DIR / "plant_classifier_validation_report.json").read_text(encoding="utf-8")
    )
    validation_error_count = validation_report["metrics"]["overall"]["sample_counts"]["incorrect_predictions"]
    report = build_report(
        "test",
        rows,
        labels,
        predictions,
        scores,
        thresholds,
        config.class_order,
        validation_error_count,
    )
    report["integrity_checks"] = {"path_leakage": 0, "group_id_leakage": 0}
    write_json(test_json_path, report)
    write_markdown(test_markdown_path, report)
    print(json.dumps({"thresholds": report["thresholds"], "metrics": report["metrics"]["overall"]}, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    validation = subparsers.add_parser("select-validation")
    validation.add_argument("--manifest", type=Path, default=DEFAULT_VALIDATION)
    validation.add_argument("--batch-size", type=int, default=32)
    verification = subparsers.add_parser("verify-frozen-validation")
    verification.add_argument("--manifest", type=Path, default=DEFAULT_VALIDATION)
    verification.add_argument("--batch-size", type=int, default=32)
    test = subparsers.add_parser("evaluate-test")
    test.add_argument("--manifest", type=Path, default=DEFAULT_TEST)
    test.add_argument("--validation-manifest", type=Path, default=DEFAULT_VALIDATION)
    test.add_argument("--batch-size", type=int, default=32)
    corrective_validation = subparsers.add_parser("select-corrective-validation")
    corrective_validation.add_argument("--manifest", type=Path, default=DEFAULT_VALIDATION)
    corrective_validation.add_argument("--batch-size", type=int, default=32)
    corrective_test = subparsers.add_parser("evaluate-corrective-test")
    corrective_test.add_argument("--manifest", type=Path, default=DEFAULT_TEST)
    corrective_test.add_argument("--validation-manifest", type=Path, default=DEFAULT_VALIDATION)
    corrective_test.add_argument("--batch-size", type=int, default=32)
    candidate_validation = subparsers.add_parser("select-candidate-validation")
    candidate_validation.add_argument(
        "--manifest", type=Path, default=DEFAULT_VALIDATION
    )
    candidate_validation.add_argument("--batch-size", type=int, default=32)
    candidate_validation.add_argument(
        "--output-dir", type=Path, default=CANDIDATE_REPORT_DIR
    )
    candidate_validation.add_argument(
        "--config-path", type=Path, default=CANDIDATE_CONFIG_PATH
    )
    candidate_test = subparsers.add_parser("evaluate-candidate-test")
    candidate_test.add_argument("--manifest", type=Path, default=DEFAULT_TEST)
    candidate_test.add_argument(
        "--validation-manifest", type=Path, default=DEFAULT_VALIDATION
    )
    candidate_test.add_argument(
        "--candidate-manifest", type=Path, default=CANDIDATE_MANIFEST_PATH
    )
    candidate_test.add_argument(
        "--frozen-config", type=Path, default=CANDIDATE_CONFIG_PATH
    )
    candidate_test.add_argument(
        "--output-dir", type=Path, default=CANDIDATE_TEST_DIR
    )
    candidate_test.add_argument(
        "--receipt-path", type=Path, default=CANDIDATE_RECEIPT_PATH
    )
    candidate_test.add_argument(
        "--regression-predictions",
        type=Path,
        default=DEFAULT_REGRESSION_PREDICTIONS,
    )
    candidate_test.add_argument("--batch-size", type=int, default=32)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("batch size must be positive")
    if args.command == "select-validation":
        run_validation(args)
    elif args.command == "verify-frozen-validation":
        verify_frozen_validation(args)
    elif args.command == "evaluate-test":
        run_test(args)
    elif args.command == "select-corrective-validation":
        run_corrective_validation(args)
    elif args.command == "select-candidate-validation":
        run_candidate_validation(args)
    elif args.command == "evaluate-candidate-test":
        run_candidate_test(args)
    else:
        run_corrective_test(args)


if __name__ == "__main__":
    main()
