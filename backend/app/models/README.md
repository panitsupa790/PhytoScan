# Runtime model bundle

The seven `.keras` files in this directory are intentionally ignored by Git.
Provision them separately during deployment using the exact filenames and
SHA-256 values in `../data/model_manifest.json`:

- `plant-classifier-v1.keras`
- `chrysanthemum-v1.keras`
- `marigold-v1.keras`
- `money-plant-v1.keras`
- `rose-v1.keras`
- `snake-plant-v1.keras`
- `spider-plant-v1.keras`

The service verifies each checksum before loading a model. All models use RGB
`float32` input in the `0..255` range, TensorFlow `decode_image`, TensorFlow
bilinear resize to `224x224`, and built-in EfficientNet normalization.
