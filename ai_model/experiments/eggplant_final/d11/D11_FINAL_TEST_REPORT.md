# D11 Final Test Report: Eggplant Disease Classifier v1

## D11 Result

**PASS**

The locked D9 R2 candidate was evaluated once on the frozen Test set. The run
performed inference only and did not train, fine-tune, augment, tune thresholds,
select a checkpoint, or change the locked pipeline.

## Lock Verification

| Artifact | Expected SHA-256 | Actual SHA-256 | Match |
|---|---|---|---|
| Final config | `5a7663db4f8c648fe06ce4d62206f7267946d357cedc6af73a6a7c35f432899b` | `5a7663db4f8c648fe06ce4d62206f7267946d357cedc6af73a6a7c35f432899b` | TRUE |
| D9 R2 checkpoint | `ae0be68277300848eb4208c5184bf9c937cbe2ea9c8d5abc363eb38976135aa5` | `ae0be68277300848eb4208c5184bf9c937cbe2ea9c8d5abc363eb38976135aa5` | TRUE |

The D5 assignment SHA-256 also matched
`26861714087fffdffd5f098f3283bba5bebe9dbb6cc93bca30dbf4cf7d14d313`.
No SHA-256 value appeared across multiple splits.

## Final Test Dataset

| Class | Images |
|---|---:|
| healthy | 208 |
| leaf_spot | 74 |
| mosaic_virus | 203 |
| **Total** | **485** |

All 485 manifest assignments matched the files under the Test directories. Each
image produced exactly one prediction.

## Final Test Performance

- Accuracy: **0.7175**
- Macro Precision: **0.6756**
- Macro Recall: **0.6799**
- Macro F1: **0.6775**
- Weighted Precision: **0.7199**
- Weighted Recall: **0.7175**
- Weighted F1: **0.7184**
- Zero-division policy: `0`

## Per-Class Performance

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| healthy | 0.7688 | 0.7356 | 0.7518 | 208 |
| leaf_spot | 0.5128 | 0.5405 | 0.5263 | 74 |
| mosaic_virus | 0.7452 | 0.7635 | 0.7543 | 203 |

## Confusion Matrix

Rows are true classes and columns are predicted classes in the locked order
`healthy`, `leaf_spot`, `mosaic_virus`:

| Actual / Predicted | healthy | leaf_spot | mosaic_virus |
|---|---:|---:|---:|
| healthy | 153 | 19 | 36 |
| leaf_spot | 17 | 40 | 17 |
| mosaic_virus | 29 | 19 | 155 |

- Healthy images were most often confused with mosaic_virus (36), then leaf_spot (19).
- Leaf spot errors were evenly split between healthy (17) and mosaic_virus (17).
- Mosaic virus images were most often confused with healthy (29), then leaf_spot (19).

The `mosaic_virus` result refers to images whose visual appearance is consistent
with that dataset class. It is not laboratory confirmation of viral infection.

## Validation vs Test

Gap is Final Test minus Validation:

| Metric | Validation R2 | Final Test | Gap |
|---|---:|---:|---:|
| Accuracy | 0.7407 | 0.7175 | -0.0232 |
| Macro F1 | 0.7156 | 0.6775 | -0.0381 |
| Leaf Spot Recall | 0.6600 | 0.5405 | -0.1195 |
| Leaf Spot F1 | 0.6168 | 0.5263 | -0.0905 |

Final Test performance is lower than validation on all four comparison metrics,
especially the minority leaf_spot class. This gap is reported as final evidence
and was not used to modify or rerun the model.

## Confidence Analysis

- Mean confidence overall: 0.7149
- Mean confidence for correct predictions: 0.7557
- Mean confidence for incorrect predictions: 0.6113
- Predictions below descriptive confidence 0.60: 141

The 0.60 value is used only for descriptive counting. It is not an inference
threshold and was not used to filter or alter predictions.

## Final Interpretation

The locked classifier correctly classified 348 of 485 Test images. Its overall
Test accuracy is 71.75% and Macro F1 is 67.75%. Healthy and mosaic_virus image
classes have similar F1 scores near 0.75, while leaf_spot remains the weakest
class with F1 0.5263. The final result shows a measurable generalization drop
from validation, so validation performance should not be presented as the
deployed model's expected performance.

## Limitations

- The dataset is imbalanced, and leaf_spot has substantially fewer training samples than the other classes.
- Exact duplicate leakage was prevented, but near-duplicate or same-leaf sequence leakage has not been fully proven absent because reliable grouping metadata is unavailable.
- `mosaic_virus` is an image-based dataset label, not a laboratory-confirmed diagnosis.
- The dataset comes from defined source collections and does not establish generalization across all cameras, cultivars, growth stages, lighting, backgrounds, regions, or field conditions.
- Confidence values are not calibrated probabilities and were used descriptively only.

## Test Set Status

**The Test set has now been used for final evaluation.**

For eggplant classifier v1, this Test set is no longer unseen. Future model
development must be treated as a new experiment generation, and this Test result
must not be reused as an unbiased evaluation after tuning.

## Tests

- D11 preflight: 12 checks passed
- Focused D11 tests: 6 passed, 0 failed
- D11 artifact validator: 25 passed, 0 failed
- Full AI test suite: 39 passed, 0 failed

## Data Safety

- Raw modified: FALSE
- Cleaned modified: FALSE
- Split modified: FALSE
- Source images overwritten, moved, renamed, or deleted: FALSE

## Git Status

- Commit: not performed
- Push: not performed
- Merge: not performed
- Auto-stage: not performed
- Unrelated Flutter generated files: untouched

## Next Recommended Phase

D12: Eggplant Model Packaging and Backend Integration using this locked model,
label mapping, P3 preprocessing, and inference contract. D12 was not started.
