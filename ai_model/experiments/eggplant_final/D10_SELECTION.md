# D10 Selection: Eggplant Final Configuration Lock

## Decision

D9 R2 is locked as the **best validation candidate** for the one-time D11 final
Test evaluation. This decision is based only on validation evidence. It is not a
statement of final model performance.

| Candidate | Configuration | Validation Macro F1 | Leaf Spot Recall |
|---|---|---:|---:|
| MobileNetV2 P3 | Frozen backbone | 0.6627 | 0.44 |
| EfficientNet-B0 P3 | Frozen backbone | 0.7040 | 0.46 |
| D9 R1 | Fine-tuning | 0.7089 | 0.52 |
| D9 R2 | Fine-tuning + class weights | **0.7156** | **0.66** |
| D9 R3 | Fine-tuning + class weights + augmentation | 0.6911 | 0.66 |

## Rationale

- R2 has the highest validation Macro F1.
- R2 raises leaf_spot recall from the EfficientNet frozen baseline's 0.46 to 0.66.
- R2 has leaf_spot F1 0.6168, the strongest D9 result for this minority class.
- R3 does not improve overall validation performance and adds augmentation complexity.
- No Test images, predictions, metrics, or error analysis were used for selection.

## Locked Artifact

- Source run: D9 R2
- Checkpoint: `ai_model/experiments/eggplant_d9_refinement/R2_class_weight/best_model.keras`
- Checkpoint SHA-256: `ae0be68277300848eb4208c5184bf9c937cbe2ea9c8d5abc363eb38976135aa5`
- Final config: `ai_model/configs/eggplant_final_locked.json`
- Final config SHA-256: recorded in `final_lock_manifest.json`
