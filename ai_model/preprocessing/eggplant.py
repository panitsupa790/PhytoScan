from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter


VARIANTS = ("P0", "P1", "P2", "P3")
INTERPOLATION = {"lanczos": Image.Resampling.LANCZOS}


class PreprocessingError(ValueError):
    pass


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_config_path() -> Path:
    return project_root() / "ai_model" / "configs" / "eggplant_preprocessing.json"


def load_config(path: Path | str | None = None) -> dict[str, Any]:
    config_path = Path(path) if path is not None else default_config_path()
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise PreprocessingError(f"Preprocessing config not found: {config_path}") from error
    except json.JSONDecodeError as error:
        raise PreprocessingError(f"Invalid preprocessing config: {error}") from error

    output = config.get("output", {})
    resize = config.get("resize", {})
    variants = config.get("variants", {})
    if output.get("color_mode") != "RGB" or output.get("dtype") != "uint8":
        raise PreprocessingError("Output must be RGB uint8")
    if output.get("model_specific_normalization") is not False:
        raise PreprocessingError("Model-specific normalization must be disabled in D6")
    if not all(isinstance(output.get(field), int) and output[field] > 0 for field in ("target_width", "target_height")):
        raise PreprocessingError("Target width and height must be positive integers")
    if resize.get("policy") != "aspect_ratio_preserving_pad":
        raise PreprocessingError("Unsupported resize policy")
    if resize.get("interpolation") not in INTERPOLATION:
        raise PreprocessingError("Unsupported resize interpolation")
    pad_color = resize.get("pad_color_rgb")
    if not isinstance(pad_color, list) or len(pad_color) != 3 or any(
        not isinstance(value, int) or not 0 <= value <= 255 for value in pad_color
    ):
        raise PreprocessingError("pad_color_rgb must contain three uint8 values")
    if set(variants) != set(VARIANTS):
        raise PreprocessingError(f"Config must define exactly: {', '.join(VARIANTS)}")
    if config.get("augmentation", {}).get("enabled") is not False:
        raise PreprocessingError("Augmentation must be disabled in D6")
    if config.get("class_balancing", {}).get("enabled") is not False:
        raise PreprocessingError("Class balancing must be disabled in D6")
    return config


def _load_rgb_image(source: Path | str | Image.Image) -> Image.Image:
    if isinstance(source, Image.Image):
        return source.copy().convert("RGB")
    if isinstance(source, (str, Path)):
        with Image.open(source) as image:
            image.load()
            return image.convert("RGB")
    raise PreprocessingError(
        "Input must be a filesystem path or PIL.Image.Image; array inputs require explicit RGB conversion"
    )


def _resize_with_padding(image: Image.Image, config: dict[str, Any]) -> Image.Image:
    output = config["output"]
    resize = config["resize"]
    target_size = (output["target_width"], output["target_height"])
    interpolation = INTERPOLATION[resize["interpolation"]]
    contained = image.copy()
    contained.thumbnail(target_size, resample=interpolation)
    canvas = Image.new("RGB", target_size, tuple(resize["pad_color_rgb"]))
    offset = (
        (target_size[0] - contained.width) // 2,
        (target_size[1] - contained.height) // 2,
    )
    canvas.paste(contained, offset)
    return canvas


def _apply_variant(
    image: Image.Image, variant: str, config: dict[str, Any]
) -> Image.Image:
    variant_config = config["variants"][variant]
    method = variant_config["method"]
    parameters = variant_config["parameters"]
    if method == "resize_only":
        return image
    if method == "median_filter":
        return image.filter(ImageFilter.MedianFilter(size=int(parameters["size"])))
    if method == "luminance_brightness_contrast":
        luminance, blue_difference, red_difference = image.convert("YCbCr").split()
        luminance = ImageEnhance.Contrast(luminance).enhance(
            float(parameters["contrast_factor"])
        )
        luminance = ImageEnhance.Brightness(luminance).enhance(
            float(parameters["brightness_factor"])
        )
        return Image.merge(
            "YCbCr", (luminance, blue_difference, red_difference)
        ).convert("RGB")
    if method == "unsharp_mask":
        return image.filter(
            ImageFilter.UnsharpMask(
                radius=float(parameters["radius"]),
                percent=int(parameters["percent"]),
                threshold=int(parameters["threshold"]),
            )
        )
    raise PreprocessingError(f"Unsupported preprocessing method: {method}")


def preprocess_image(
    source: Path | str | Image.Image,
    variant: str,
    config: dict[str, Any] | None = None,
) -> Image.Image:
    active_config = config if config is not None else load_config()
    if variant not in VARIANTS:
        raise PreprocessingError(
            f"Unsupported preprocessing variant {variant!r}; choose from {', '.join(VARIANTS)}"
        )
    image = _load_rgb_image(source)
    resized = _resize_with_padding(image, active_config)
    result = _apply_variant(resized, variant, active_config)
    if result.mode != "RGB" or result.size != (
        active_config["output"]["target_width"],
        active_config["output"]["target_height"],
    ):
        raise PreprocessingError("Preprocessing produced an invalid output format")
    return result
