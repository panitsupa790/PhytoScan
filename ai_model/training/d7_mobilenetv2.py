from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import random
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "1")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sklearn
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from preprocessing.eggplant import VARIANTS, load_config as load_preprocessing_config
from preprocessing.eggplant import preprocess_image


ALLOWED_SPLITS = ("train", "val")


class D7Error(RuntimeError):
    pass


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_config_path() -> Path:
    return project_root() / "ai_model" / "configs" / "eggplant_mobilenetv2_d7.json"


def canonical_json_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_training_config(path: Path | str | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else default_config_path()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["preprocessing"]["variants"] != list(VARIANTS):
        raise D7Error("D7 must define exactly P0-P3 in order")
    if config["preprocessing"]["augmentation_enabled"] is not False:
        raise D7Error("Augmentation must remain disabled in D7")
    if config["preprocessing"]["class_balancing_enabled"] is not False:
        raise D7Error("Class balancing must remain disabled in D7")
    if config["model"]["backbone_trainable"] is not False:
        raise D7Error("The MobileNetV2 backbone must be frozen in D7")
    if config["data"]["image_size"] != [224, 224] or config["data"]["channels"] != 3:
        raise D7Error("D7 input must be 224x224x3")
    if config["data"]["expected_counts"].get("test") != 0:
        raise D7Error("D7 test image access expectation must be zero")
    return config


@dataclass(frozen=True)
class ImageRecord:
    split: str
    class_name: str
    class_index: int
    filename: str
    path: Path


def load_records(config: dict[str, Any], splits: Iterable[str]) -> list[ImageRecord]:
    requested = tuple(splits)
    if not requested or any(split not in ALLOWED_SPLITS for split in requested):
        raise D7Error("Only train and val records may be requested in D7")
    root = project_root()
    manifest_path = root / config["data"]["manifest"]
    split_root = (root / config["data"]["split_root"]).resolve()
    class_indices = {name: index for index, name in enumerate(config["classes"])}
    records: list[ImageRecord] = []
    with manifest_path.open("r", encoding="utf-8", newline="") as csv_file:
        for row in csv.DictReader(csv_file):
            split = row["split"]
            if split not in requested:
                continue
            class_name = row["class"]
            if class_name not in class_indices:
                raise D7Error(f"Unknown class in manifest: {class_name}")
            path = (split_root / split / class_name / row["filename"]).resolve()
            allowed_root = (split_root / split).resolve()
            if path != allowed_root and allowed_root not in path.parents:
                raise D7Error(f"Unsafe manifest path: {path}")
            if not path.is_file():
                raise D7Error(f"Missing split image: {path}")
            records.append(
                ImageRecord(split, class_name, class_indices[class_name], row["filename"], path)
            )
    records.sort(key=lambda row: (row.class_index, row.filename.casefold(), row.filename))
    return records


def stratified_sample(records: list[ImageRecord], per_class: int, seed: int) -> list[ImageRecord]:
    rng = random.Random(seed)
    selected: list[ImageRecord] = []
    class_names = sorted({record.class_name for record in records})
    for class_name in class_names:
        candidates = [record for record in records if record.class_name == class_name]
        if len(candidates) < per_class:
            raise D7Error(f"Not enough {class_name} records for smoke test")
        selected.extend(rng.sample(candidates, per_class))
    return sorted(selected, key=lambda row: (row.class_index, row.filename.casefold()))


@dataclass
class AccessAudit:
    split_root: Path
    paths: dict[str, set[str]] = field(
        default_factory=lambda: {"train": set(), "val": set(), "test": set()}
    )
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, path: Path, split: str) -> None:
        if split not in ALLOWED_SPLITS:
            raise D7Error(f"Image-byte access denied for split: {split}")
        resolved = path.resolve()
        allowed_root = (self.split_root / split).resolve()
        if allowed_root not in resolved.parents:
            raise D7Error(f"Image path is outside allowed {split} root: {resolved}")
        with self._lock:
            self.paths[split].add(resolved.as_posix())

    def summary(self) -> dict[str, Any]:
        return {
            "unique_paths_accessed": {name: len(paths) for name, paths in self.paths.items()},
            "test_image_bytes_accessed": 0,
            "policy": "Only train and val image bytes are loadable; test is rejected before I/O",
        }


def make_dataset(
    records: list[ImageRecord],
    variant: str,
    config: dict[str, Any],
    preprocessing_config: dict[str, Any],
    audit: AccessAudit,
    training: bool,
) -> tf.data.Dataset:
    if variant not in VARIANTS:
        raise D7Error(f"Unsupported preprocessing variant: {variant}")
    if not records or any(record.split not in ALLOWED_SPLITS for record in records):
        raise D7Error("Dataset contains an empty or forbidden split selection")
    split_names = {record.split for record in records}
    if len(split_names) != 1:
        raise D7Error("Build train and validation datasets separately")
    split = next(iter(split_names))
    paths = [str(record.path) for record in records]
    labels = [record.class_index for record in records]
    height, width = config["data"]["image_size"]

    def load_rgb(path_value: np.ndarray, label_value: np.ndarray) -> tuple[np.ndarray, np.int32]:
        raw_path = path_value.item() if hasattr(path_value, "item") else path_value
        path = Path(raw_path.decode("utf-8") if isinstance(raw_path, bytes) else str(raw_path))
        audit.record(path, split)
        image = preprocess_image(path, variant, preprocessing_config)
        array = np.asarray(image, dtype=np.uint8)
        if array.shape != (height, width, 3):
            raise D7Error(f"Invalid D6 output shape: {array.shape}")
        return array, np.int32(label_value)

    def load_tensor(path: tf.Tensor, label: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
        image, output_label = tf.numpy_function(
            load_rgb, [path, label], [tf.uint8, tf.int32]
        )
        image.set_shape((height, width, 3))
        output_label.set_shape(())
        return image, output_label

    def normalize(image: tf.Tensor, label: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
        normalized = tf.keras.applications.mobilenet_v2.preprocess_input(
            tf.cast(image, tf.float32)
        )
        return normalized, label

    dataset = tf.data.Dataset.from_tensor_slices((paths, labels))
    options = tf.data.Options()
    options.experimental_deterministic = True
    dataset = dataset.with_options(options).map(load_tensor, num_parallel_calls=1).cache()
    if training:
        dataset = dataset.shuffle(
            len(records), seed=config["seed"], reshuffle_each_iteration=True
        )
    dataset = dataset.batch(config["training"]["batch_size"], drop_remainder=False)
    dataset = dataset.map(normalize, num_parallel_calls=tf.data.AUTOTUNE)
    return dataset.prefetch(tf.data.AUTOTUNE)


def set_reproducibility(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    tf.keras.utils.set_random_seed(seed)
    tf.config.experimental.enable_op_determinism()


def build_model(config: dict[str, Any], weights: str | None = "imagenet") -> tf.keras.Model:
    height, width = config["data"]["image_size"]
    inputs = tf.keras.Input(shape=(height, width, config["data"]["channels"]), name="rgb_input")
    backbone = tf.keras.applications.MobileNetV2(
        input_shape=(height, width, 3), include_top=False, weights=weights
    )
    backbone.trainable = False
    features = backbone(inputs, training=False)
    pooled = tf.keras.layers.GlobalAveragePooling2D(name="global_average_pool")(features)
    dropped = tf.keras.layers.Dropout(config["model"]["dropout_rate"], name="dropout")(pooled)
    outputs = tf.keras.layers.Dense(
        len(config["classes"]), activation="softmax", name="disease_probabilities"
    )(dropped)
    model = tf.keras.Model(inputs, outputs, name="eggplant_mobilenetv2_d7")
    optimizer = tf.keras.optimizers.Adam(learning_rate=config["training"]["learning_rate"])
    model.compile(
        optimizer=optimizer,
        loss=config["training"]["loss"],
        metrics=["accuracy"],
    )
    return model


def build_frozen_feature_models(
    config: dict[str, Any], weights: str | None = "imagenet"
) -> tuple[tf.keras.Model, tf.keras.Model, tf.keras.Model]:
    height, width = config["data"]["image_size"]
    inputs = tf.keras.Input(shape=(height, width, 3), name="rgb_input")
    backbone = tf.keras.applications.MobileNetV2(
        input_shape=(height, width, 3), include_top=False, weights=weights
    )
    backbone.trainable = False
    feature_map = backbone(inputs, training=False)
    pooled = tf.keras.layers.GlobalAveragePooling2D(name="global_average_pool")(feature_map)
    feature_extractor = tf.keras.Model(inputs, pooled, name="frozen_mobilenetv2_features")

    feature_inputs = tf.keras.Input(shape=(int(pooled.shape[-1]),), name="pooled_features")
    dropped = tf.keras.layers.Dropout(
        config["model"]["dropout_rate"], name="dropout"
    )(feature_inputs)
    probabilities = tf.keras.layers.Dense(
        len(config["classes"]), activation="softmax", name="disease_probabilities"
    )(dropped)
    head = tf.keras.Model(feature_inputs, probabilities, name="classification_head")
    head.compile(
        optimizer=tf.keras.optimizers.Adam(
            learning_rate=config["training"]["learning_rate"]
        ),
        loss=config["training"]["loss"],
        metrics=["accuracy"],
    )
    full_model = tf.keras.Model(
        inputs, head(feature_extractor(inputs, training=False)), name="eggplant_mobilenetv2_d7"
    )
    return feature_extractor, head, full_model


def parameter_counts(model: tf.keras.Model) -> dict[str, int]:
    trainable = int(sum(np.prod(variable.shape) for variable in model.trainable_weights))
    non_trainable = int(sum(np.prod(variable.shape) for variable in model.non_trainable_weights))
    return {"total": trainable + non_trainable, "trainable": trainable, "non_trainable": non_trainable}


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def plot_history(history: dict[str, list[float]], output_path: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(11, 4))
    epochs = range(1, len(history["loss"]) + 1)
    axes[0].plot(epochs, history["loss"], label="train")
    axes[0].plot(epochs, history["val_loss"], label="validation")
    axes[0].set(title="Loss", xlabel="Epoch", ylabel="Sparse cross-entropy")
    axes[1].plot(epochs, history["accuracy"], label="train")
    axes[1].plot(epochs, history["val_accuracy"], label="validation")
    axes[1].set(title="Accuracy", xlabel="Epoch", ylabel="Accuracy", ylim=(0, 1))
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def plot_confusion(matrix: np.ndarray, classes: list[str], output_path: Path, normalized: bool) -> None:
    values = matrix.astype(float)
    if normalized:
        row_sums = values.sum(axis=1, keepdims=True)
        values = np.divide(values, row_sums, out=np.zeros_like(values), where=row_sums != 0)
    figure, axis = plt.subplots(figsize=(6, 5))
    image = axis.imshow(values, cmap="Blues", vmin=0, vmax=1 if normalized else None)
    figure.colorbar(image, ax=axis)
    axis.set(xticks=range(len(classes)), yticks=range(len(classes)), xticklabels=classes, yticklabels=classes)
    axis.set_xlabel("Predicted label")
    axis.set_ylabel("True label")
    axis.set_title("Validation confusion matrix" + (" (row-normalized)" if normalized else ""))
    threshold = values.max() / 2 if values.size else 0
    for row in range(len(classes)):
        for column in range(len(classes)):
            label = f"{values[row, column]:.2f}" if normalized else str(int(values[row, column]))
            axis.text(column, row, label, ha="center", va="center", color="white" if values[row, column] > threshold else "black")
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def evaluate_predictions(labels: np.ndarray, predictions: np.ndarray, classes: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]], np.ndarray]:
    predicted_labels = predictions.argmax(axis=1)
    report = classification_report(
        labels,
        predicted_labels,
        labels=list(range(len(classes))),
        target_names=classes,
        output_dict=True,
        zero_division=0,
    )
    rows = []
    for name in [*classes, "macro avg", "weighted avg"]:
        row = report[name]
        rows.append({"label": name, "precision": row["precision"], "recall": row["recall"], "f1_score": row["f1-score"], "support": int(row["support"])})
    metrics = {
        "validation_accuracy": float(accuracy_score(labels, predicted_labels)),
        "validation_macro_precision": float(precision_score(labels, predicted_labels, average="macro", zero_division=0)),
        "validation_macro_recall": float(recall_score(labels, predicted_labels, average="macro", zero_division=0)),
        "validation_macro_f1": float(f1_score(labels, predicted_labels, average="macro", zero_division=0)),
        "validation_weighted_f1": float(f1_score(labels, predicted_labels, average="weighted", zero_division=0)),
        "per_class": {
            name: {"precision": float(report[name]["precision"]), "recall": float(report[name]["recall"]), "f1": float(report[name]["f1-score"]), "support": int(report[name]["support"])}
            for name in classes
        },
    }
    return metrics, rows, confusion_matrix(labels, predicted_labels, labels=list(range(len(classes))))


def run_variant(variant: str, config: dict[str, Any], output_dir: Path, smoke: bool = False) -> dict[str, Any]:
    if variant not in config["preprocessing"]["variants"]:
        raise D7Error(f"Unknown D7 variant: {variant}")
    tf.keras.backend.clear_session()
    set_reproducibility(config["seed"])
    preprocessing_path = project_root() / config["preprocessing"]["config"]
    preprocessing_config = load_preprocessing_config(preprocessing_path)
    train_records = load_records(config, [config["data"]["train_split"]])
    val_records = load_records(config, [config["data"]["validation_split"]])
    if smoke:
        smoke_config = config["smoke_test"]
        train_records = stratified_sample(train_records, smoke_config["train_per_class"], config["seed"])
        val_records = stratified_sample(val_records, smoke_config["validation_per_class"], config["seed"])
    else:
        expected = config["data"]["expected_counts"]
        if len(train_records) != expected["train"] or len(val_records) != expected["val"]:
            raise D7Error("Train/validation counts differ from the locked D5 split")

    output_dir.mkdir(parents=True, exist_ok=True)
    audit = AccessAudit((project_root() / config["data"]["split_root"]).resolve())
    train_dataset = make_dataset(train_records, variant, config, preprocessing_config, audit, training=False)
    val_dataset = make_dataset(val_records, variant, config, preprocessing_config, audit, training=False)
    feature_extractor, head, model = build_frozen_feature_models(
        config, weights=config["model"]["weights"]
    )
    counts = parameter_counts(model)
    checkpoint_path = output_dir / "best_model.keras"
    head_checkpoint_path = output_dir / "best_head.keras"
    callbacks: list[tf.keras.callbacks.Callback] = [
        tf.keras.callbacks.ModelCheckpoint(
            head_checkpoint_path, monitor="val_loss", save_best_only=True, verbose=1
        ),
    ]
    if not smoke:
        callbacks.append(
            tf.keras.callbacks.EarlyStopping(
                monitor=config["training"]["early_stopping_monitor"],
                patience=config["training"]["early_stopping_patience"],
                restore_best_weights=config["training"]["restore_best_weights"],
                verbose=1,
            )
    )
    epochs = config["smoke_test"]["epochs"] if smoke else config["training"]["max_epochs"]
    started = time.perf_counter()
    train_features = feature_extractor.predict(
        train_dataset.map(lambda images, labels: images), verbose=1
    )
    val_features = feature_extractor.predict(
        val_dataset.map(lambda images, labels: images), verbose=1
    )
    feature_seconds = time.perf_counter() - started
    set_reproducibility(config["seed"])
    history_object = head.fit(
        train_features,
        np.array([record.class_index for record in train_records], dtype=np.int32),
        validation_data=(
            val_features,
            np.array([record.class_index for record in val_records], dtype=np.int32),
        ),
        batch_size=config["training"]["batch_size"],
        epochs=epochs,
        callbacks=callbacks,
        verbose=2,
        shuffle=config["training"]["shuffle_train"],
    )
    duration_seconds = time.perf_counter() - started
    best_head = tf.keras.models.load_model(head_checkpoint_path)
    head.set_weights(best_head.get_weights())
    model.save(checkpoint_path)
    predictions = best_head.predict(val_features, verbose=0)
    labels = np.array([record.class_index for record in val_records], dtype=np.int32)
    metrics, report_rows, matrix = evaluate_predictions(labels, predictions, config["classes"])
    history = {name: [float(value) for value in values] for name, values in history_object.history.items()}
    best_epoch = int(np.argmin(history["val_loss"]) + 1)
    metrics.update({"variant": variant, "smoke_test": smoke, "best_epoch": best_epoch, "epochs_ran": len(history["loss"]), "feature_extraction_seconds": feature_seconds, "duration_seconds": duration_seconds})

    access_summary = audit.summary()
    expected_access = {"train": len(train_records), "val": len(val_records), "test": 0}
    if access_summary["unique_paths_accessed"] != expected_access:
        raise D7Error(f"Unexpected image access audit: {access_summary['unique_paths_accessed']}")
    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "history.json", history)
    write_csv(output_dir / "history.csv", ["epoch", *history.keys()], ({"epoch": index + 1, **{name: values[index] for name, values in history.items()}} for index in range(len(history["loss"]))))
    write_csv(output_dir / "classification_report.csv", ["label", "precision", "recall", "f1_score", "support"], report_rows)
    matrix_rows = [{"actual": name, **{classes_name: int(matrix[row, column]) for column, classes_name in enumerate(config["classes"])}} for row, name in enumerate(config["classes"])]
    write_csv(output_dir / "confusion_matrix.csv", ["actual", *config["classes"]], matrix_rows)
    normalized = matrix.astype(float) / matrix.sum(axis=1, keepdims=True)
    normalized_rows = [{"actual": name, **{classes_name: float(normalized[row, column]) for column, classes_name in enumerate(config["classes"])}} for row, name in enumerate(config["classes"])]
    write_csv(output_dir / "confusion_matrix_normalized.csv", ["actual", *config["classes"]], normalized_rows)
    plot_history(history, output_dir / "training_curves.png")
    plot_confusion(matrix, config["classes"], output_dir / "confusion_matrix.png", False)
    plot_confusion(matrix, config["classes"], output_dir / "confusion_matrix_normalized.png", True)
    write_json(output_dir / "image_access_audit.json", access_summary)
    (output_dir / "model_summary.txt").write_text(_model_summary(model), encoding="utf-8")
    metadata = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "variant": variant,
        "smoke_test": smoke,
        "seed": config["seed"],
        "training_config_sha256": canonical_json_hash(config),
        "preprocessing_config_sha256": canonical_json_hash(preprocessing_config),
        "train_samples": len(train_records),
        "validation_samples": len(val_records),
        "test_image_bytes_accessed": 0,
        "parameter_counts": counts,
        "backbone_frozen": True,
        "augmentation_enabled": False,
        "class_balancing_enabled": False,
        "model_normalization": config["preprocessing"]["model_normalization"],
        "tensorflow_version": tf.__version__,
        "keras_version": tf.keras.__version__,
        "scikit_learn_version": sklearn.__version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "physical_devices": [str(device) for device in tf.config.list_physical_devices()],
    }
    write_json(output_dir / "run_metadata.json", metadata)
    write_json(output_dir / "config_snapshot.json", config)
    return {"metrics": metrics, "metadata": metadata, "access": access_summary}


def _model_summary(model: tf.keras.Model) -> str:
    lines: list[str] = []
    model.summary(print_fn=lines.append)
    return "\n".join(lines) + "\n"
