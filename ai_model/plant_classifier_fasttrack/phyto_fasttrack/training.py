from __future__ import annotations

import gc
import platform
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from sklearn.metrics import f1_score, recall_score

from .core import (
    CLASS_NAMES,
    FastTrackError,
    ImageRecord,
    build_balanced_schedule,
    canonical_json_hash,
    configure_reproducibility,
    sha256_file,
    utc_now,
    write_json,
)
from .evaluation import evaluate_model, make_inference_dataset, prediction_metrics


def configure_tensorflow(config: dict[str, Any]) -> dict[str, Any]:
    import tensorflow as tf

    gpus = tf.config.list_physical_devices("GPU")
    for gpu in gpus:
        try:
            tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError:
            pass
    if config["training"].get("mixed_precision", True) and gpus:
        tf.keras.mixed_precision.set_global_policy("mixed_float16")
    else:
        tf.keras.mixed_precision.set_global_policy("float32")
    return {
        "gpu_devices": [device.name for device in gpus],
        "mixed_precision_policy": tf.keras.mixed_precision.global_policy().name,
    }


def make_training_dataset(records: Sequence[ImageRecord], batch_size: int, seed: int):
    import tensorflow as tf

    paths = [str(record.path) for record in records]
    labels = [record.class_index for record in records]

    def decode(path: "tf.Tensor", label: "tf.Tensor"):
        data = tf.io.read_file(path)
        image = tf.io.decode_image(data, channels=3, expand_animations=False)
        image.set_shape([None, None, 3])
        image = tf.cast(image, tf.float32)
        image = tf.image.resize(image, [224, 224], method="bilinear", antialias=False)
        return image, label

    options = tf.data.Options()
    options.experimental_deterministic = True
    dataset = tf.data.Dataset.from_tensor_slices((paths, labels)).with_options(options)
    dataset = dataset.shuffle(len(records), seed=seed, reshuffle_each_iteration=True)
    dataset = dataset.map(decode, num_parallel_calls=tf.data.AUTOTUNE)
    return dataset.batch(batch_size, drop_remainder=False).prefetch(2)


def build_fresh_model(config: dict[str, Any], weights: str | None = "imagenet"):
    import tensorflow as tf

    augmentation = config["augmentation"]
    inputs = tf.keras.Input(shape=(224, 224, 3), name="rgb_0_255")
    x = tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal_and_vertical", seed=config["seed"], name="leaf_flip"),
            tf.keras.layers.RandomRotation(
                factor=float(augmentation["rotation_factor"]),
                fill_mode="reflect",
                seed=config["seed"] + 1,
                name="leaf_rotation",
            ),
            tf.keras.layers.RandomZoom(
                height_factor=(-float(augmentation["zoom_factor"]), float(augmentation["zoom_factor"])),
                width_factor=(-float(augmentation["zoom_factor"]), float(augmentation["zoom_factor"])),
                fill_mode="reflect",
                seed=config["seed"] + 2,
                name="leaf_zoom",
            ),
            tf.keras.layers.RandomBrightness(
                factor=float(augmentation["brightness_factor"]),
                value_range=(0.0, 255.0),
                seed=config["seed"] + 3,
                name="leaf_brightness",
            ),
            tf.keras.layers.RandomContrast(
                factor=float(augmentation["contrast_factor"]),
                seed=config["seed"] + 4,
                name="leaf_contrast",
            ),
        ],
        name="controlled_leaf_augmentation",
    )(inputs)
    backbone = tf.keras.applications.EfficientNetB0(
        include_top=False,
        weights=weights,
        input_shape=(224, 224, 3),
    )
    backbone.trainable = False
    x = backbone(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D(name="global_average_pool")(x)
    x = tf.keras.layers.Dropout(float(config["model"]["dropout_rate"]), name="dropout")(x)
    outputs = tf.keras.layers.Dense(len(CLASS_NAMES), activation="softmax", dtype="float32", name="plant_probabilities")(x)
    return tf.keras.Model(inputs, outputs, name="fresh_imagenet_efficientnetb0"), backbone


def compile_model(model: Any, learning_rate: float) -> None:
    import tensorflow as tf

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy")],
    )


class ValidationMacroMetrics:
    """Factory used to avoid importing TensorFlow when only preflight is run."""

    @staticmethod
    def build(validation_dataset: Any, validation_labels: np.ndarray):
        import tensorflow as tf

        class Callback(tf.keras.callbacks.Callback):
            def on_epoch_end(self, epoch: int, logs: dict[str, Any] | None = None) -> None:
                logs = logs if logs is not None else {}
                scores = np.asarray(
                    self.model.predict(validation_dataset.map(lambda image, label: image), verbose=0),
                    dtype=np.float32,
                )
                predicted = scores.argmax(axis=1)
                logs["val_macro_f1"] = float(
                    f1_score(
                        validation_labels,
                        predicted,
                        labels=np.arange(len(CLASS_NAMES)),
                        average="macro",
                        zero_division=0,
                    )
                )
                logs["val_min_class_recall"] = float(
                    recall_score(
                        validation_labels,
                        predicted,
                        labels=np.arange(len(CLASS_NAMES)),
                        average=None,
                        zero_division=0,
                    ).min()
                )
                print(
                    f" - val_macro_f1: {logs['val_macro_f1']:.4f}"
                    f" - val_min_class_recall: {logs['val_min_class_recall']:.4f}"
                )

        return Callback()


def _callbacks(checkpoint: Path, validation_dataset: Any, validation_labels: np.ndarray, patience: int):
    import tensorflow as tf

    return [
        ValidationMacroMetrics.build(validation_dataset, validation_labels),
        tf.keras.callbacks.ModelCheckpoint(
            checkpoint,
            monitor="val_macro_f1",
            mode="max",
            save_best_only=True,
            verbose=1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_macro_f1",
            mode="max",
            patience=patience,
            restore_best_weights=True,
            verbose=1,
        ),
        tf.keras.callbacks.TerminateOnNaN(),
    ]


def _history_dict(history: Any) -> dict[str, list[float]]:
    return {name: [float(value) for value in values] for name, values in history.history.items()}


def _checkpoint_metrics(path: Path, validation_dataset: Any, labels: np.ndarray) -> dict[str, Any]:
    import tensorflow as tf

    model = tf.keras.models.load_model(path, compile=False)
    probabilities = np.asarray(
        model.predict(validation_dataset.map(lambda image, label: image), verbose=0), dtype=np.float32
    )
    metrics, _ = prediction_metrics(labels, probabilities)
    del model
    gc.collect()
    return metrics


def train_fresh_b0(
    *,
    config: dict[str, Any],
    train_records: Sequence[ImageRecord],
    validation_records: Sequence[ImageRecord],
    run_dir: Path,
    preflight_report: dict[str, Any],
) -> dict[str, Any]:
    import tensorflow as tf

    if not preflight_report.get("passed"):
        raise FastTrackError("Training is fail-closed because development validation did not pass preflight")
    if run_dir.exists():
        raise FastTrackError(f"Refusing to overwrite training run: {run_dir}")
    run_dir.mkdir(parents=True)
    seed = int(config["seed"])
    configure_reproducibility(seed)
    runtime = configure_tensorflow(config)
    scheduled, sampling_receipt = build_balanced_schedule(
        train_records,
        seed=seed,
        max_repeats_per_image=int(config["sampling"]["max_repeats_per_image"]),
    )
    write_json(run_dir / "sampling_receipt.json", sampling_receipt)
    batch_size = int(config["training"]["batch_size"])
    train_dataset = make_training_dataset(scheduled, batch_size, seed)
    validation_dataset = make_inference_dataset(validation_records, batch_size)
    validation_labels = np.asarray([record.class_index for record in validation_records], dtype=np.int64)

    model, backbone = build_fresh_model(config)
    compile_model(model, float(config["training"]["head_learning_rate"]))
    head_checkpoint = run_dir / "head_best.keras"
    started = time.perf_counter()
    head_history = model.fit(
        train_dataset,
        validation_data=validation_dataset,
        epochs=int(config["training"]["head_epochs"]),
        callbacks=_callbacks(
            head_checkpoint,
            validation_dataset,
            validation_labels,
            int(config["training"]["early_stopping_patience"]),
        ),
        verbose=2,
    )
    write_json(run_dir / "head_history.json", _history_dict(head_history))

    model = tf.keras.models.load_model(head_checkpoint, compile=False)
    backbone = model.get_layer("efficientnetb0")
    backbone.trainable = True
    tail_layers = int(config["training"]["fine_tune_tail_layers"])
    cutoff = max(0, len(backbone.layers) - tail_layers)
    for index, layer in enumerate(backbone.layers):
        layer.trainable = index >= cutoff and not isinstance(layer, tf.keras.layers.BatchNormalization)
    compile_model(model, float(config["training"]["fine_tune_learning_rate"]))
    fine_tune_checkpoint = run_dir / "fine_tune_best.keras"
    fine_tune_history = model.fit(
        train_dataset,
        validation_data=validation_dataset,
        epochs=int(config["training"]["fine_tune_epochs"]),
        callbacks=_callbacks(
            fine_tune_checkpoint,
            validation_dataset,
            validation_labels,
            int(config["training"]["early_stopping_patience"]),
        ),
        verbose=2,
    )
    write_json(run_dir / "fine_tune_history.json", _history_dict(fine_tune_history))

    head_metrics = _checkpoint_metrics(head_checkpoint, validation_dataset, validation_labels)
    fine_tune_metrics = _checkpoint_metrics(fine_tune_checkpoint, validation_dataset, validation_labels)
    candidates = [(head_checkpoint, head_metrics), (fine_tune_checkpoint, fine_tune_metrics)]
    selected_path, selected_metrics = max(
        candidates,
        key=lambda item: (item[1]["macro_f1"], item[1]["per_class_recall"] and min(item[1]["per_class_recall"].values()), item[1]["accuracy"]),
    )
    receipt = {
        "schema_version": 1,
        "completed_at_utc": utc_now(),
        "duration_seconds": time.perf_counter() - started,
        "fresh_imagenet_initialization": True,
        "loaded_v2_to_v5_weights": False,
        "class_order": list(CLASS_NAMES),
        "seed": seed,
        "config_sha256": canonical_json_hash(config),
        "train_manifest_sha256": preflight_report["artifacts"]["train_manifest_sha256"],
        "development_manifest_sha256": preflight_report["artifacts"]["development_manifest_sha256"],
        "runtime": {
            **runtime,
            "tensorflow": tf.__version__,
            "keras": getattr(tf.keras, "__version__", "unknown"),
            "python": sys.version,
            "platform": platform.platform(),
        },
        "checkpoints": {
            "head": {"path": str(head_checkpoint), "sha256": sha256_file(head_checkpoint), "metrics": head_metrics},
            "fine_tune": {"path": str(fine_tune_checkpoint), "sha256": sha256_file(fine_tune_checkpoint), "metrics": fine_tune_metrics},
            "selected": {"path": str(selected_path), "sha256": sha256_file(selected_path), "metrics": selected_metrics},
        },
        "selection_rule": "highest development macro_f1, then minimum per-class recall, then accuracy",
        "batch_normalization_frozen_during_fine_tune": True,
        "legacy_or_locked_test_accessed": False,
        "deployment_performed": False,
    }
    write_json(run_dir / "training_receipt.json", receipt)
    return receipt


def evaluate_selected_training_checkpoint(
    *,
    training_receipt: dict[str, Any],
    validation_records: Sequence[ImageRecord],
    manifest_path: Path,
    output_dir: Path,
    batch_size: int,
) -> dict[str, Any]:
    selected = Path(training_receipt["checkpoints"]["selected"]["path"])
    return evaluate_model(
        model_path=selected,
        records=validation_records,
        manifest_path=manifest_path,
        output_dir=output_dir,
        dataset_role="eligible_development_validation",
        batch_size=batch_size,
        notes=["Used for model development; not a locked or legacy test result."],
    )
