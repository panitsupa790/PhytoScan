# Phase 1 Pre-Flutter Verification

## Outcome

Phase 1 is not yet cleared for Flutter integration. A preprocessing parity bug
was found and fixed in Backend, but the previously frozen threshold was selected
with the old Pillow preprocessing and is therefore invalid for the corrected
runtime contract. The Test set was not reopened and the threshold was not
changed during this audit.

## Notebook/backend classification discrepancy

The Plant Classifier model is identical in all locations. The Notebook source
checkpoint, Desktop export, runtime file, and manifest all use SHA-256
`5585bb91835006003e6f052c58465d84fc0d9ac6e37227d842a28d18f3991165`.
Class order is identical: chrysanthemum, marigold, money_plant, rose,
snake_plant, spider_plant. Manifest row order and each row's plant/label mapping
are valid.

The discrepancy came from image preprocessing:

- Notebook: `tf.io.decode_image(channels=3)` -> `float32` ->
  `tf.image.resize(..., bilinear, 224x224)`.
- Backend before fix: Pillow decode -> `convert("RGB")` -> Pillow bilinear
  resize -> `float32`.

All 2,340 Validation images had at least one pixel difference after resize.
The maximum absolute pixel delta was 190.0647. The maximum output probability
delta was 0.743466, and seven rows changed top-1 prediction.

The TensorFlow pipeline reproduces the Notebook result exactly: 2,333 correct
and 7 errors. The old Pillow pipeline reproduces the previous Backend result:
2,338 correct and 2 errors. This rules out model SHA, label mapping, manifest
ordering, RGB channel count, and prediction/label alignment as the cause.

The environments are not identical: the Notebook environment currently has
TensorFlow 2.22.0-rc0, Keras 3.16.0.dev2026100104, and Pillow 12.3.0, while the
Backend uses TensorFlow 2.21.0, Keras 3.15.1, and Pillow 11.2.1. NumPy is 2.5.3
in both. Backend TensorFlow preprocessing still reproduced the Notebook's seven
Validation top-1 errors, so version differences are not the source of the 7 vs
2 discrepancy, though small probability-level numerical differences can remain.

The same preprocessing mismatch explains the Notebook Test result of 1,573/1,580
(7 errors) versus the old Backend report of 1,577/1,580 (3 errors). Test was not
run again during this audit because the locked protocol allowed one Test
evaluation only; row-level Test parity therefore remains intentionally
unverified.

## Frozen threshold verification

The frozen values were not changed:

- `MIN_CONFIDENCE = 0.0`
- `MIN_MARGIN = 0.4026440382003784`

Using these unchanged values with the corrected Notebook-compatible pipeline on
Validation gives:

- Coverage: 2,329/2,340 (99.5299%)
- Accepted Accuracy: 2,325/2,329 (99.8283%)
- Accepted Errors: 4
- FAR among incorrect predictions: 4/7 (57.1429%)
- Correct Rejections: 3/7 (42.8571%)
- Wrongful Rejections: 8/2,333 (0.3429%)

The old frozen config no longer satisfies its required Accepted Errors = 0
criterion. Runtime automatic routing now fails closed because that config does
not contain the corrected TensorFlow input contract. Manual confirmed routing
remains available for supported plant codes.

## Router/API verification

- `manual_confirmation_required` returns before any disease classifier call.
- A supplied `plant_code` is normalized and checked against the active six-plant
  registry; unsupported codes are rejected.
- For multiple images, every image must pass both thresholds and every top-1
  plant must match. Mixed plant predictions return
  `manual_confirmation_required`; their disease probabilities are never
  averaged together.
- Image validation runs before inference.

## Deployment verification

All seven runtime `.keras` files match their Desktop export and manifest
SHA-256. All class orders and exported input metadata match. Real model-loading
tests pass for the Plant Classifier and all six Disease Classifiers.

The `.keras` files are ignored by Git. A deployment must provision all seven
artifacts separately and verify them against `model_manifest.json`; cloning the
repository alone is insufficient.

## Automated tests

`62 passed in 20.06s` on Python 3.12.4, TensorFlow 2.21.0, Keras 3.15.1,
Pillow 11.2.1, and NumPy 2.5.3. See `automated_test_results.txt`.

## Required before Phase 2

1. Re-run the locked Exact Observed-Boundary Search on Validation using the
   corrected TensorFlow preprocessing and freeze a new config. This must be a
   deterministic Validation-only operation.
2. Decide and document whether the previous one-time Test evaluation may be
   replaced because it used an invalid preprocessing implementation. Do not use
   the known Test result to choose or adjust the new threshold.
3. If a corrected Test run is authorized, evaluate exactly once with the newly
   frozen config and preserve row-level predictions for auditability.
4. Configure deployment artifact delivery for the seven ignored `.keras`
   files and run the bundle verifier in the target environment.
5. Keep Unsupported/OOD rejection claims disabled until a dedicated dataset is
   available.

No Flutter/Mobile files, model weights, datasets, split manifests, or disease
guidance were modified during this verification.
