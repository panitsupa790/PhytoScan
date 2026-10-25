# D10 Report: Final Configuration Lock

## D10 Result

**PASS**

D9 R2 was locked as the best validation candidate. D10 performed no training,
inference, image decoding, or Test evaluation.

## Locked Model

- Architecture: EfficientNet-B0
- Pretrained weights: ImageNet
- Input: 224x224x3
- Head: GlobalAveragePooling2D, Dropout 0.2, Dense 3, softmax
- Checkpoint: `ai_model/experiments/eggplant_d9_refinement/R2_class_weight/best_model.keras`
- Checkpoint SHA-256: `ae0be68277300848eb4208c5184bf9c937cbe2ea9c8d5abc363eb38976135aa5`
- Checkpoint load: successful
- Output classes: 3

## Locked Preprocessing

- Variant: P3
- Output: RGB uint8 `[0,255]`
- Resize: preserve aspect ratio and pad to 224x224
- Interpolation: Lanczos
- Padding: white RGB `[255,255,255]`
- Sharpening: Unsharp Mask, radius 1.0, percent 60, threshold 3

The model pipeline casts P3 output to float32 without changing its `[0,255]`
range. Under TensorFlow 2.21, EfficientNet `preprocess_input` is identity and the
loaded backbone contains internal `Rescaling(1/255)` and `Normalization` layers.
MobileNetV2 preprocessing is not used.

## Locked Class Mapping

| Index | Class |
|---:|---|
| 0 | healthy |
| 1 | leaf_spot |
| 2 | mosaic_virus |

## Locked Fine-tuning

- Fine-tuned backbone window: top 20 layers
- Weight-bearing backbone layers unfrozen: 7
- BatchNormalization: all 49 layers frozen
- Optimizer: Adam
- Learning rate: `1e-5`
- Loss: sparse categorical cross-entropy
- Batch size: 32
- Augmentation: OFF
- Seed: 42

## Locked Class Weights

Formula: `N / (number_of_classes * count_i)`, calculated from Train only.

| Class | Weight |
|---|---:|
| healthy | 0.7779916586461341 |
| leaf_spot | 2.178796046720575 |
| mosaic_virus | 0.7963875205254516 |

## Final Config

- Path: `ai_model/configs/eggplant_final_locked.json`
- SHA-256: `5a7663db4f8c648fe06ce4d62206f7267946d357cedc6af73a6a7c35f432899b`
- Hash scope: exact config file bytes
- Lock manifest: `ai_model/experiments/eggplant_final/final_lock_manifest.json`

D11 must verify both the config and checkpoint hashes before decoding any Test
image. A mismatch requires aborting before Test access.

## Selection Evidence

| Candidate | Validation Macro F1 | Leaf Spot Recall |
|---|---:|---:|
| MobileNetV2 P3 | 0.6627 | 0.44 |
| EfficientNet-B0 P3 | 0.7040 | 0.46 |
| D9 R1 | 0.7089 | 0.52 |
| D9 R2 | **0.7156** | **0.66** |
| D9 R3 | 0.6911 | 0.66 |

R2 has the highest validation Macro F1, materially improves leaf_spot recall over
the frozen EfficientNet baseline, and avoids R3's validation regression and added
augmentation complexity. Test data was not used for this decision. These values
are validation evidence, not final performance.

## Test Protocol

- Protocol: `ai_model/experiments/eggplant_final/D11_TEST_PROTOCOL.md`
- Test total: 485
- healthy: 208
- leaf_spot: 74
- mosaic_virus: 203
- Test image bytes accessed during D10: **0**
- Test images decoded during D10: **0**
- Test inference performed: **FALSE**
- Final Test evaluation performed: **FALSE**

## Tests

- Focused D10 tests: 8 passed, 0 failed
- D10 acceptance validator: 17 passed, 0 failed
- Full AI test suite: 33 passed, 0 failed

## Data Safety

- Train metadata count: 2,425
- Validation metadata count: 324
- Test metadata count: 485
- Raw modified: FALSE
- Cleaned modified: FALSE
- Split modified: FALSE

The source safety check used path, size, and modification-time metadata. It did
not open Test image bytes, preserving the stricter D10 zero-access rule.

## Git Status

- Commit: not performed
- Push: not performed
- Merge: not performed
- Auto-stage: not performed
- Unrelated Flutter generated files: untouched

## Next Phase

D11: Final Test Evaluation using only the locked config and locked checkpoint.
D11 was not started.
