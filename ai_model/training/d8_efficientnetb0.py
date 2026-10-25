from __future__ import annotations

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


VARIANTS = ("P0", "P3")


class D8Error(D7Error):
    pass


def default_config_path() -> Path:
    return project_root() / "ai_model" / "configs" / "eggplant_efficientnetb0_d8_lite.json"


def load_training_config(path: Path | str | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else default_config_path()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["preprocessing"]["variants"] != list(VARIANTS):
        raise D8Error("D8 Lite must define exactly P0 and P3")
    if config["preprocessing"]["augmentation_enabled"] is not False:
        raise D8Error("Augmentation must remain disabled in D8 Lite")
    if config["preprocessing"]["class_balancing_enabled"] is not False:
        raise D8Error("Class balancing must remain disabled in D8 Lite")
    if config["model"]["backbone_trainable"] is not False:
        raise D8Error("EfficientNetB0 backbone must remain frozen")
    if config["data"]["image_size"] != [224, 224] or config["data"]["channels"] != 3:
        raise D8Error("D8 Lite input must be 224x224x3")
    if config["data"]["expected_counts"].get("test") != 0:
        raise D8Error("D8 Lite test image access expectation must be zero")
    if config["preprocessing"]["model_normalization"] != "keras_efficientnet_internal_rescaling":
        raise D8Error("EfficientNet normalization policy is not locked")
    return config


def make_dataset(
    records: list[ImageRecord],
    variant: str,
    config: dict[str, Any],
    preprocessing_config: dict[str, Any],
    audit: AccessAudit,
) -> tf.data.Dataset:
    if variant not in VARIANTS:
        raise D8Error(f"Unsupported D8 Lite variant: {variant}")
    if not records or any(record.split not in ("train", "val") for record in records):
        raise D8Error("Only non-empty train or val records are allowed")
    split_names = {record.split for record in records}
    if len(split_names) != 1:
        raise D8Error("Build train and validation datasets separately")
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
            raise D8Error(f"Invalid D6 output shape: {array.shape}")
        return array, np.int32(label_value)

    def load_tensor(path: tf.Tensor, label: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
        image, output_label = tf.numpy_function(load_rgb, [path, label], [tf.uint8, tf.int32])
        image.set_shape((height, width, 3))
        output_label.set_shape(())
        return image, output_label

    def prepare_efficientnet_input(image: tf.Tensor, label: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
        float_image = tf.cast(image, tf.float32)
        prepared = tf.keras.applications.efficientnet.preprocess_input(float_image)
        return prepared, label

    dataset = tf.data.Dataset.from_tensor_slices((paths, labels))
    options = tf.data.Options()
    options.experimental_deterministic = True
    dataset = dataset.with_options(options).map(load_tensor, num_parallel_calls=1).cache()
    dataset = dataset.batch(config["training"]["batch_size"], drop_remainder=False)
    dataset = dataset.map(prepare_efficientnet_input, num_parallel_calls=tf.data.AUTOTUNE)
    return dataset.prefetch(tf.data.AUTOTUNE)


def build_frozen_feature_models(
    config: dict[str, Any], weights: str | None = "imagenet"
) -> tuple[tf.keras.Model, tf.keras.Model, tf.keras.Model]:
    height, width = config["data"]["image_size"]
    inputs = tf.keras.Input(shape=(height, width, 3), name="rgb_0_255_input")
    backbone = tf.keras.applications.EfficientNetB0(
        input_shape=(height, width, 3), include_top=False, weights=weights
    )
    backbone.trainable = False
    feature_map = backbone(inputs, training=False)
    pooled = tf.keras.layers.GlobalAveragePooling2D(name="global_average_pool")(feature_map)
    feature_extractor = tf.keras.Model(inputs, pooled, name="frozen_efficientnetb0_features")

    feature_inputs = tf.keras.Input(shape=(int(pooled.shape[-1]),), name="pooled_features")
    dropped = tf.keras.layers.Dropout(config["model"]["dropout_rate"], name="dropout")(feature_inputs)
    outputs = tf.keras.layers.Dense(
        len(config["classes"]), activation="softmax", name="disease_probabilities"
    )(dropped)
    head = tf.keras.Model(feature_inputs, outputs, name="classification_head")
    head.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=config["training"]["learning_rate"]),
        loss=config["training"]["loss"],
        metrics=["accuracy"],
    )
    full_model = tf.keras.Model(
        inputs, head(feature_extractor(inputs, training=False)), name="eggplant_efficientnetb0_d8_lite"
    )
    return feature_extractor, head, full_model


def _model_summary(model: tf.keras.Model) -> str:
    lines: list[str] = []
    model.summary(print_fn=lines.append)
    return "\n".join(lines) + "\n"


def run_variant(variant: str, config: dict[str, Any], output_dir: Path, smoke: bool = False) -> dict[str, Any]:
    if variant not in VARIANTS:
        raise D8Error(f"Unknown D8 Lite variant: {variant}")
    tf.keras.backend.clear_session()
    set_reproducibility(config["seed"])
    preprocessing_config = load_preprocessing_config(project_root() / config["preprocessing"]["config"])
    train_records = load_records(config, [config["data"]["train_split"]])
    val_records = load_records(config, [config["data"]["validation_split"]])
    if smoke:
        smoke_config = config["smoke_test"]
        train_records = stratified_sample(train_records, smoke_config["train_per_class"], config["seed"])
        val_records = stratified_sample(val_records, smoke_config["validation_per_class"], config["seed"])
    else:
        expected = config["data"]["expected_counts"]
        if len(train_records) != expected["train"] or len(val_records) != expected["val"]:
            raise D8Error("Train/validation counts differ from the locked D5 split")

    output_dir.mkdir(parents=True, exist_ok=True)
    audit = AccessAudit((project_root() / config["data"]["split_root"]).resolve())
    train_dataset = make_dataset(train_records, variant, config, preprocessing_config, audit)
    val_dataset = make_dataset(val_records, variant, config, preprocessing_config, audit)
    feature_extractor, head, full_model = build_frozen_feature_models(config, config["model"]["weights"])
    counts = parameter_counts(full_model)
    head_checkpoint = output_dir / "best_head.keras"
    callbacks: list[tf.keras.callbacks.Callback] = [
        tf.keras.callbacks.ModelCheckpoint(head_checkpoint, monitor="val_loss", save_best_only=True, verbose=1)
    ]
    if not smoke:
        callbacks.append(tf.keras.callbacks.EarlyStopping(
            monitor=config["training"]["early_stopping_monitor"],
            patience=config["training"]["early_stopping_patience"],
            restore_best_weights=config["training"]["restore_best_weights"],
            verbose=1,
        ))
    epochs = config["smoke_test"]["epochs"] if smoke else config["training"]["max_epochs"]
    started = time.perf_counter()
    train_features = feature_extractor.predict(train_dataset.map(lambda images, labels: images), verbose=1)
    val_features = feature_extractor.predict(val_dataset.map(lambda images, labels: images), verbose=1)
    feature_seconds = time.perf_counter() - started
    set_reproducibility(config["seed"])
    train_labels = np.array([record.class_index for record in train_records], dtype=np.int32)
    val_labels = np.array([record.class_index for record in val_records], dtype=np.int32)
    history_object = head.fit(
        train_features,
        train_labels,
        validation_data=(val_features, val_labels),
        batch_size=config["training"]["batch_size"],
        epochs=epochs,
        callbacks=callbacks,
        verbose=2,
        shuffle=config["training"]["shuffle_train"],
    )
    duration_seconds = time.perf_counter() - started
    best_head = tf.keras.models.load_model(head_checkpoint)
    head.set_weights(best_head.get_weights())
    full_model.save(output_dir / "best_model.keras")
    predictions = best_head.predict(val_features, verbose=0)
    metrics, report_rows, matrix = evaluate_predictions(val_labels, predictions, config["classes"])
    history = {name: [float(value) for value in values] for name, values in history_object.history.items()}
    best_epoch = int(np.argmin(history["val_loss"]) + 1)
    metrics.update({
        "variant": variant,
        "smoke_test": smoke,
        "best_epoch": best_epoch,
        "epochs_ran": len(history["loss"]),
        "feature_extraction_seconds": feature_seconds,
        "duration_seconds": duration_seconds,
    })
    access = audit.summary()
    expected_access = {"train": len(train_records), "val": len(val_records), "test": 0}
    if access["unique_paths_accessed"] != expected_access:
        raise D8Error(f"Unexpected image access audit: {access['unique_paths_accessed']}")

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "history.json", history)
    write_csv(output_dir / "history.csv", ["epoch", *history.keys()], (
        {"epoch": index + 1, **{name: values[index] for name, values in history.items()}}
        for index in range(len(history["loss"]))
    ))
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
    (output_dir / "model_summary.txt").write_text(_model_summary(full_model), encoding="utf-8")
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
        "normalization_verified": "TF 2.21 preprocess_input is identity; EfficientNetB0 contains Rescaling(1/255) and Normalization layers",
        "tensorflow_version": tf.__version__,
        "keras_version": tf.keras.__version__,
        "scikit_learn_version": sklearn.__version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "physical_devices": [str(device) for device in tf.config.list_physical_devices()],
    }
    write_json(output_dir / "run_metadata.json", metadata)
    write_json(output_dir / "config_snapshot.json", config)
    return {"metrics": metrics, "metadata": metadata, "access": access}
