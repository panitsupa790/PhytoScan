from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import sklearn
import tensorflow as tf

from preprocessing.eggplant import load_config as load_preprocessing_config
from preprocessing.eggplant import preprocess_image
from training.d7_mobilenetv2 import (
    AccessAudit,
    D7Error,
    ImageRecord,
    canonical_json_hash,
    evaluate_predictions,
    load_records,
    parameter_counts,
    plot_confusion,
    plot_history,
    project_root,
    set_reproducibility,
    stratified_sample,
    write_csv,
    write_json,
)


RUN_IDS = ("R1", "R2", "R3")


class D9Error(D7Error):
    pass


def default_config_path() -> Path:
    return project_root() / "ai_model" / "configs" / "eggplant_d9_refinement.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_training_config(path: Path | str | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else default_config_path()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if tuple(config["runs"]) != RUN_IDS:
        raise D9Error("D9 must define exactly R1, R2, and R3 in order")
    if config["source"]["preprocessing_variant"] != "P3":
        raise D9Error("D9 preprocessing must remain P3")
    if config["model"]["top_layer_window"] != 20 or not config["model"]["freeze_batch_normalization"]:
        raise D9Error("D9 fine-tuning layer policy is not locked")
    if config["training"]["learning_rate"] != 1e-5 or config["training"]["max_epochs"] != 20:
        raise D9Error("D9 fine-tuning schedule is not locked")
    if config["data"]["expected_counts"].get("test") != 0:
        raise D9Error("D9 test image access expectation must be zero")
    classes = config["classes"]
    if classes != ["healthy", "leaf_spot", "mosaic_virus"]:
        raise D9Error("D9 class order differs from D8")
    return config


def calculate_class_weights(config: dict[str, Any]) -> dict[int, float]:
    counts = config["data"]["train_class_counts"]
    total = sum(counts.values())
    class_count = len(config["classes"])
    if total != config["data"]["expected_counts"]["train"]:
        raise D9Error("Class-weight counts do not equal the locked train total")
    return {
        index: total / (class_count * counts[class_name])
        for index, class_name in enumerate(config["classes"])
    }


def build_augmentation(config: dict[str, Any]) -> tf.keras.Sequential:
    settings = config["augmentation"]
    seed = config["seed"]
    return tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal", seed=seed),
            tf.keras.layers.RandomRotation(
                settings["rotation_degrees"] / 360.0,
                fill_mode=settings["fill_mode"],
                interpolation=settings["interpolation"],
                seed=seed + 1,
            ),
            tf.keras.layers.RandomZoom(
                height_factor=(-settings["zoom_fraction"], settings["zoom_fraction"]),
                width_factor=(-settings["zoom_fraction"], settings["zoom_fraction"]),
                fill_mode=settings["fill_mode"],
                interpolation=settings["interpolation"],
                seed=seed + 2,
            ),
            tf.keras.layers.RandomTranslation(
                height_factor=settings["translation_height_fraction"],
                width_factor=settings["translation_width_fraction"],
                fill_mode=settings["fill_mode"],
                interpolation=settings["interpolation"],
                seed=seed + 3,
            ),
        ],
        name="mild_train_only_augmentation",
    )


def make_dataset(
    records: list[ImageRecord],
    config: dict[str, Any],
    preprocessing_config: dict[str, Any],
    audit: AccessAudit,
    training: bool,
    augmentation_enabled: bool,
) -> tf.data.Dataset:
    if not records or any(record.split not in ("train", "val") for record in records):
        raise D9Error("Only non-empty train or val records are allowed")
    split_names = {record.split for record in records}
    if len(split_names) != 1:
        raise D9Error("Build train and validation datasets separately")
    split = next(iter(split_names))
    if augmentation_enabled and (not training or split != "train"):
        raise D9Error("Augmentation is permitted only for the training split")
    paths = [str(record.path) for record in records]
    labels = [record.class_index for record in records]
    height, width = config["data"]["image_size"]

    def load_rgb(path_value: np.ndarray, label_value: np.ndarray) -> tuple[np.ndarray, np.int32]:
        raw_path = path_value.item() if hasattr(path_value, "item") else path_value
        path = Path(raw_path.decode("utf-8") if isinstance(raw_path, bytes) else str(raw_path))
        audit.record(path, split)
        image = preprocess_image(path, "P3", preprocessing_config)
        array = np.asarray(image, dtype=np.uint8)
        if array.shape != (height, width, 3):
            raise D9Error(f"Invalid P3 output shape: {array.shape}")
        return array, np.int32(label_value)

    def load_tensor(path: tf.Tensor, label: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
        image, output_label = tf.numpy_function(load_rgb, [path, label], [tf.uint8, tf.int32])
        image.set_shape((height, width, 3))
        output_label.set_shape(())
        return image, output_label

    dataset = tf.data.Dataset.from_tensor_slices((paths, labels))
    options = tf.data.Options()
    options.experimental_deterministic = True
    dataset = dataset.with_options(options).map(load_tensor, num_parallel_calls=1).cache()
    if training and config["training"]["shuffle_train"]:
        dataset = dataset.shuffle(len(records), seed=config["seed"], reshuffle_each_iteration=True)
    dataset = dataset.batch(config["training"]["batch_size"], drop_remainder=False)
    dataset = dataset.map(lambda images, output_labels: (tf.cast(images, tf.float32), output_labels), num_parallel_calls=1)
    if augmentation_enabled:
        augmentation = build_augmentation(config)
        dataset = dataset.map(
            lambda images, output_labels: (augmentation(images, training=True), output_labels),
            num_parallel_calls=1,
        )
    return dataset.prefetch(1)


def load_and_configure_model(config: dict[str, Any]) -> tuple[tf.keras.Model, dict[str, Any]]:
    checkpoint = project_root() / config["source"]["checkpoint"]
    actual_hash = sha256_file(checkpoint)
    if actual_hash != config["source"]["checkpoint_sha256"]:
        raise D9Error("R0 source checkpoint hash mismatch")
    model = tf.keras.models.load_model(checkpoint, compile=False)
    extractor = model.get_layer(config["model"]["feature_extractor_layer_name"])
    backbone = extractor.get_layer(config["model"]["backbone_layer_name"])
    backbone.trainable = True
    for layer in backbone.layers:
        layer.trainable = False
    window = backbone.layers[-config["model"]["top_layer_window"] :]
    for layer in window:
        if not isinstance(layer, tf.keras.layers.BatchNormalization):
            layer.trainable = True
    extractor.trainable = True
    model.get_layer(config["model"]["head_layer_name"]).trainable = True
    for layer in backbone.layers:
        if isinstance(layer, tf.keras.layers.BatchNormalization):
            layer.trainable = False
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=config["training"]["learning_rate"]),
        loss=config["training"]["loss"],
        metrics=["accuracy"],
    )
    policy = {
        "backbone_total_layers": len(backbone.layers),
        "top_layer_window": config["model"]["top_layer_window"],
        "window_first_index": len(backbone.layers) - len(window),
        "window_layer_names": [layer.name for layer in window],
        "trainable_window_layers": [layer.name for layer in window if layer.trainable],
        "trainable_weight_layers": [layer.name for layer in window if layer.trainable and layer.weights],
        "batch_normalization_total": sum(isinstance(layer, tf.keras.layers.BatchNormalization) for layer in backbone.layers),
        "batch_normalization_trainable": sum(isinstance(layer, tf.keras.layers.BatchNormalization) and layer.trainable for layer in backbone.layers),
        "source_checkpoint_sha256": actual_hash,
    }
    return model, policy


def _model_summary(model: tf.keras.Model) -> str:
    lines: list[str] = []
    model.summary(print_fn=lines.append, expand_nested=True)
    return "\n".join(lines) + "\n"


def run_experiment(run_id: str, config: dict[str, Any], output_dir: Path, smoke: bool = False) -> dict[str, Any]:
    if run_id not in RUN_IDS:
        raise D9Error(f"Unknown D9 run: {run_id}")
    run_config = config["runs"][run_id]
    tf.keras.backend.clear_session()
    set_reproducibility(config["seed"])
    preprocessing_config = load_preprocessing_config(project_root() / config["source"]["preprocessing_config"])
    train_records = load_records(config, [config["data"]["train_split"]])
    val_records = load_records(config, [config["data"]["validation_split"]])
    if smoke:
        settings = config["smoke_test"]
        train_records = stratified_sample(train_records, settings["train_per_class"], config["seed"])
        val_records = stratified_sample(val_records, settings["validation_per_class"], config["seed"])
    elif len(train_records) != 2425 or len(val_records) != 324:
        raise D9Error("Train/validation counts differ from the locked split")
    output_dir.mkdir(parents=True, exist_ok=True)
    audit = AccessAudit((project_root() / config["data"]["split_root"]).resolve())
    train_dataset = make_dataset(train_records, config, preprocessing_config, audit, True, run_config["augmentation"])
    val_dataset = make_dataset(val_records, config, preprocessing_config, audit, False, False)
    model, fine_tune_policy = load_and_configure_model(config)
    counts = parameter_counts(model)
    checkpoint = output_dir / "best_model.keras"
    callbacks: list[tf.keras.callbacks.Callback] = [
        tf.keras.callbacks.ModelCheckpoint(checkpoint, monitor="val_loss", save_best_only=True, verbose=1)
    ]
    if not smoke:
        callbacks.append(tf.keras.callbacks.EarlyStopping(
            monitor=config["training"]["early_stopping_monitor"],
            patience=config["training"]["early_stopping_patience"],
            restore_best_weights=config["training"]["restore_best_weights"],
            verbose=1,
        ))
    class_weights = calculate_class_weights(config) if run_config["class_weights"] else None
    epochs = config["smoke_test"]["epochs"] if smoke else config["training"]["max_epochs"]
    started = time.perf_counter()
    history_object = model.fit(
        train_dataset,
        validation_data=val_dataset,
        epochs=epochs,
        callbacks=callbacks,
        class_weight=class_weights,
        verbose=2,
        shuffle=False,
    )
    duration_seconds = time.perf_counter() - started
    best_model = tf.keras.models.load_model(checkpoint, compile=False)
    predictions = best_model.predict(val_dataset, verbose=0)
    val_labels = np.array([record.class_index for record in val_records], dtype=np.int32)
    metrics, report_rows, matrix = evaluate_predictions(val_labels, predictions, config["classes"])
    history = {name: [float(value) for value in values] for name, values in history_object.history.items()}
    best_epoch = int(np.argmin(history["val_loss"]) + 1)
    metrics.update({"run": run_id, "technique": run_config["technique"], "smoke_test": smoke, "best_epoch": best_epoch, "epochs_ran": len(history["loss"]), "training_time_seconds": duration_seconds})
    access = audit.summary()
    expected_access = {"train": len(train_records), "val": len(val_records), "test": 0}
    if access["unique_paths_accessed"] != expected_access:
        raise D9Error(f"Unexpected image access audit: {access['unique_paths_accessed']}")

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "history.json", history)
    write_csv(output_dir / "history.csv", ["epoch", *history.keys()], ({"epoch": index + 1, **{name: values[index] for name, values in history.items()}} for index in range(len(history["loss"]))))
    write_csv(output_dir / "classification_report.csv", ["label", "precision", "recall", "f1_score", "support"], report_rows)
    matrix_rows = [{"actual": name, **{class_name: int(matrix[row, column]) for column, class_name in enumerate(config["classes"])}} for row, name in enumerate(config["classes"])]
    write_csv(output_dir / "confusion_matrix.csv", ["actual", *config["classes"]], matrix_rows)
    normalized = matrix.astype(float) / matrix.sum(axis=1, keepdims=True)
    normalized_rows = [{"actual": name, **{class_name: float(normalized[row, column]) for column, class_name in enumerate(config["classes"])}} for row, name in enumerate(config["classes"])]
    write_csv(output_dir / "confusion_matrix_normalized.csv", ["actual", *config["classes"]], normalized_rows)
    plot_history(history, output_dir / "training_curves.png")
    plot_confusion(matrix, config["classes"], output_dir / "confusion_matrix.png", False)
    plot_confusion(matrix, config["classes"], output_dir / "confusion_matrix_normalized.png", True)
    write_json(output_dir / "image_access_audit.json", access)
    write_json(output_dir / "fine_tune_policy.json", fine_tune_policy)
    write_json(output_dir / "class_weights.json", {"enabled": class_weights is not None, "formula": config["class_weights"]["formula"], "weights_by_index": class_weights, "weights_by_class": {name: class_weights[index] for index, name in enumerate(config["classes"])} if class_weights else {}})
    write_json(output_dir / "augmentation.json", {"enabled": run_config["augmentation"], "scope": "train_only" if run_config["augmentation"] else "off", "parameters": config["augmentation"] if run_config["augmentation"] else {}})
    (output_dir / "model_summary.txt").write_text(_model_summary(model), encoding="utf-8")
    metadata = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(), "run": run_id,
        "technique": run_config["technique"], "smoke_test": smoke, "seed": config["seed"],
        "training_config_sha256": canonical_json_hash(config),
        "preprocessing_config_sha256": canonical_json_hash(preprocessing_config),
        "source_checkpoint_sha256": fine_tune_policy["source_checkpoint_sha256"],
        "train_samples": len(train_records), "validation_samples": len(val_records),
        "test_image_bytes_accessed": 0, "parameter_counts": counts,
        "class_weights_enabled": run_config["class_weights"],
        "augmentation_enabled": run_config["augmentation"], "validation_augmentation_enabled": False,
        "batch_normalization_trainable": fine_tune_policy["batch_normalization_trainable"],
        "tensorflow_version": tf.__version__, "keras_version": tf.keras.__version__,
        "scikit_learn_version": sklearn.__version__, "python_version": sys.version,
        "platform": platform.platform(), "physical_devices": [str(device) for device in tf.config.list_physical_devices()],
    }
    write_json(output_dir / "run_metadata.json", metadata)
    write_json(output_dir / "config_snapshot.json", config)
    return {"metrics": metrics, "metadata": metadata, "access": access}
