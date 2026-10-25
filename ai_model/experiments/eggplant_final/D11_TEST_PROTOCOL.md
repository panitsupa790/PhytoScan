# D11 Protocol: One-Time Final Test Evaluation

## Purpose

Evaluate the D10 locked eggplant classifier once on the frozen 485-image Test
set. D11 is evaluation only: it must not train, fine-tune, select, or tune.

## Frozen Inputs

- Config: `ai_model/configs/eggplant_final_locked.json`
- Config hash: read from `ai_model/experiments/eggplant_final/final_lock_manifest.json`
- Checkpoint: D9 R2 best checkpoint referenced by the locked config
- Preprocessing: locked P3
- Class mapping: `healthy`, `leaf_spot`, `mosaic_virus`
- Test counts: healthy 208, leaf_spot 74, mosaic_virus 203; total 485

## Required Sequence

1. Read the lock manifest and locked config without opening Test image bytes.
2. Recompute the exact-file SHA-256 of the locked config and require a match.
3. Recompute the R2 checkpoint SHA-256 and require a match.
4. Validate lock status, class mapping, P3 parameters, model input/output, and Test counts.
5. Abort before Test decoding if any lock check fails.
6. Load the verified checkpoint without compiling for training.
7. Load each of the 485 Test images through locked P3: RGB, aspect-ratio-preserving resize/pad to 224x224, Lanczos, white padding, Unsharp Mask radius 1.0, percent 60, threshold 3.
8. Convert P3 output to float32 while preserving the `[0,255]` range. Do not apply MobileNetV2 normalization; EfficientNet-B0 performs Rescaling(1/255) and Normalization internally.
9. Run inference only. Use the locked class order and softmax argmax; do not tune thresholds.
10. Compute Accuracy, Macro Precision, Macro Recall, Macro F1, Weighted F1, and per-class Precision/Recall/F1/Support.
11. Save the raw and normalized confusion matrices and classification report.
12. Record Test access as exactly 485 unique images and mark the Test set as opened.

## Prohibited Actions

- No training, fine-tuning, data augmentation, resampling, or class-weight changes.
- No preprocessing, architecture, checkpoint, class-order, or threshold changes.
- No checkpoint selection based on Test results.
- No repeated Test runs for tuning or model selection.
- No inspection of Test errors followed by retraining and reuse of the same result as unbiased evaluation.

## After Test Access

Once D11 opens the Test set, its result is for **final evaluation only**. Any
subsequent model development must be treated as a new experiment generation,
and this Test set must not be described as unseen for that new generation.
