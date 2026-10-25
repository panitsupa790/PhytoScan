# D9 Lite Report: EfficientNet-B0 Candidate Refinement

## D9 Result

**PASS**

R1, R2, and R3 trained successfully from the same D8 R0 checkpoint. Evaluation
used the fixed validation set only. No Test image bytes or Test metrics were used.

## Fine-tuning Configuration

- Source checkpoint: D8 EfficientNet-B0 + P3 best checkpoint
- Source SHA-256: `c30bfc8839ba91bb4ced173375aeb2b95098e57d4eea32a326e4f23ec1bb0496`
- Backbone: EfficientNet-B0, ImageNet initialized in D8
- Fine-tuning window: top 20 backbone layers, indices 218-237
- Weight-bearing backbone layers unfrozen: 7
- BatchNormalization: all 49 backbone BatchNorm layers frozen
- Trainable parameters including classification head: 1,346,611
- Optimizer: Adam
- Learning rate: `1e-5`
- Epoch limit: 20
- Early stopping: validation loss, patience 5, restore best weights
- Batch size: 32
- Seed: 42
- Preprocessing: locked P3, RGB resize/pad 224x224 with Lanczos and Unsharp Mask
- Model-specific normalization: unchanged EfficientNet-B0 internal preprocessing

The same layer policy, optimizer, learning rate, batch size, loss, validation set,
seed, and P3 preprocessing were used for R1-R3. Each run independently restored
R0; no run continued from another D9 run.

## Class Weights

Balanced inverse-frequency weights were calculated from the 2,425 Train samples
only using `N / (number_of_classes * count_i)`:

| Class | Train count | Weight |
|---|---:|---:|
| healthy | 1,039 | 0.777992 |
| leaf_spot | 371 | 2.178796 |
| mosaic_virus | 1,015 | 0.796388 |

Class weights were OFF for R1 and ON only for R2/R3. No resampling was used.

## Augmentation

R3 alone used online, in-memory Train augmentation:

- Horizontal flip
- Rotation up to approximately +/-10 degrees
- Zoom up to approximately +/-10%
- Height and width translation up to approximately +/-5%
- Bilinear interpolation with reflect fill

Validation augmentation was OFF. No random color, brightness, sharpening, blur,
crop, vertical flip, or disk-backed augmented dataset was used.

## Results

| Run | Technique | Accuracy | Macro F1 | Leaf Spot Recall | Leaf Spot F1 | Best Epoch |
|---|---|---:|---:|---:|---:|---:|
| R0 | Frozen baseline | 0.7407 | 0.7040 | 0.46 | 0.5897 | 15 |
| R1 | Fine-tuning | 0.7438 | 0.7089 | 0.52 | 0.5909 | 12 |
| R2 | + Class Weight | 0.7407 | **0.7156** | **0.66** | **0.6168** | 1 |
| R3 | + Augmentation | 0.7191 | 0.6911 | **0.66** | 0.5841 | 7 |

The complete comparison, including Macro Precision/Recall, Weighted F1, per-class
recalls, and training time, is in `comparison/d9_refinement_comparison.csv`.

## Confusion Matrix Findings

- R0 correctly classified 23/50 leaf_spot images; 20 were confused as healthy and 7 as mosaic_virus.
- R1 correctly classified 26/50; the main leaf_spot confusion remained healthy (15), followed by mosaic_virus (9).
- R2 correctly classified 33/50; errors fell to 11 as healthy and 6 as mosaic_virus. This is the strongest leaf_spot result.
- R3 also classified 33/50 correctly, but produced more false-positive leaf_spot predictions and reduced mosaic_virus recall to 0.6296.

## Training Behavior

- R0 showed only a small late validation-loss increase after its best epoch.
- R1 improved gradually to epoch 12, then showed mild overfitting: training accuracy continued upward while validation loss rose.
- R2 reached its lowest validation loss at epoch 1 and stopped at epoch 6. Later epochs did not improve validation loss, so restoring the first checkpoint was important.
- R3 improved through epoch 7, then validation loss rose for five epochs. Its small final accuracy gap does not indicate severe overfitting, but augmentation reduced validation performance in this controlled setup.

Training curves and confusion matrices are retained in each run directory.

## Best Validation Candidate

**R2: EfficientNet-B0 + P3 + fine-tuning + balanced class weights** is the best
validation candidate. It has the highest Macro F1 (0.7156), improves leaf_spot
recall from 0.46 to 0.66, and has the best leaf_spot F1 (0.6168). Its Macro F1
lead over R1 is approximately 0.0067, which is outside the `< 0.005` close-result
rule. R3 adds complexity while reducing Macro F1 and validation accuracy.

This is not a final model selection because the frozen Test set has not been
evaluated.

## Test Freeze

- Train images used per run: 2,425
- Validation images used per run: 324
- Test image bytes accessed: **0**
- Test predictions, confusion matrices, and metrics: **not created**
- Final Test evaluation: **FALSE**

## Data Safety

- Raw modified: FALSE
- Cleaned modified: FALSE
- Split modified: FALSE

The before/after audit compared paths, sizes, and modification times. It did not
hash image bytes because opening frozen Test bytes would violate the stricter D9
zero-access requirement.

## Tests

- D9 acceptance validation: 34 passed, 0 failed
- Focused D9 unit tests: 6 passed, 0 failed
- Full AI test suite (D6-D9): 25 passed, 0 failed
- Best checkpoints R1-R3: loadable, 3-class outputs
- R1-R3 training curves and confusion-matrix images: visually inspected and valid

## Git Status

- Commit: not performed
- Push: not performed
- Merge: not performed
- Auto-stage: not performed
- Unrelated Flutter files: untouched

## Next Recommended Phase

D10: lock the R2 training configuration. Only after that lock should the final
Test evaluation be run once on the 485 frozen Test images. D10 was not started.
