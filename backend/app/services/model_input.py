from __future__ import annotations

import numpy as np
import tensorflow as tf


class ModelInputError(ValueError):
    pass


SUPPORTED_EMBEDDED_PREPROCESSING = {
    # Legacy name retained for the active EfficientNet bundle.
    "efficientnet_0_255",
    # Explicit names used by candidate manifests. Both contracts receive raw
    # RGB float32 [0, 255]; normalization is embedded in the checkpoint.
    "efficientnet_embedded_rescaling_from_0_255",
    "mobilenet_v2_embedded_minus1_1_from_0_255",
}


def prepare_model_input(
    content: bytes,
    input_shape: tuple[int, int, int],
    preprocessing: str,
    decoder: str,
    resize_method: str,
) -> np.ndarray:
    height, width, channels = input_shape
    if (
        channels != 3
        or preprocessing not in SUPPORTED_EMBEDDED_PREPROCESSING
        or decoder != "tensorflow_decode_image_rgb"
        or resize_method != "tensorflow_bilinear"
    ):
        raise ModelInputError("Unsupported model input contract")
    try:
        image = tf.io.decode_image(
            tf.convert_to_tensor(content, dtype=tf.string),
            channels=3,
            expand_animations=False,
        )
        image.set_shape([None, None, 3])
        resized = tf.image.resize(
            tf.cast(image, tf.float32),
            [height, width],
            method=tf.image.ResizeMethod.BILINEAR,
            antialias=False,
        )
        array = np.asarray(resized, dtype=np.float32)
    except (tf.errors.InvalidArgumentError, TypeError, ValueError) as error:
        raise ModelInputError("Image could not be decoded or resized") from error
    if array.shape != input_shape or not np.isfinite(array).all():
        raise ModelInputError("Preprocessing output is invalid")
    return array
