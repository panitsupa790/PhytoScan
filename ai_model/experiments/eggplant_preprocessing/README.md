# Eggplant Preprocessing Experiment Protocol

## Scope

D6 defines four deterministic image-processing variants for controlled model
experiments. It does not train a model or select a winning variant. Outputs are
RGB `uint8` images in `[0, 255]`; model-specific normalization is deferred to
the model pipeline.

## Fair Comparison

Every variant uses the same aspect-ratio-preserving resize to `224x224` with
white padding and Lanczos interpolation. Each controlled experiment must apply
one variant consistently to both train and validation data:

- `P0`: resize only.
- `P1`: resize plus mild `3x3` median filtering.
- `P2`: resize plus mild luminance-channel brightness and contrast adjustment.
- `P3`: resize plus mild unsharp masking.

Parameters are defined only in `ai_model/configs/eggplant_preprocessing.json`.
Preprocessing is deterministic. Augmentation and class balancing are disabled.

## Dataset Use

The fixed visual sanity sample uses five train images per class with seed `42`.
No test image may be used to choose methods or parameters. The test set is
frozen and may only receive a locked preprocessing configuration during final
evaluation.

Future augmentation must run after splitting and only on train. Validation is
used for model selection, preprocessing comparison, and early stopping.

## Interpretation

Preview statistics detect implementation errors and extreme artifacts only.
They do not measure classification performance and cannot establish a best
preprocessing variant. Exact-duplicate leakage was prevented in D5, but no
deep near-duplicate or same-leaf sequence analysis is available without
reliable grouping metadata.
