# D7 Result

PASS

Four controlled MobileNetV2 runs were completed for P0-P3. Selection used the
validation set only. No test image bytes were accessed.

## Environment

- Python 3.12.4
- TensorFlow 2.21.0 / Keras 3.15.1
- Device used: CPU (native Windows TensorFlow does not expose the RTX 4050)
- Seed: 42

## Model Configuration

- MobileNetV2, ImageNet weights, `include_top=false`
- Frozen backbone
- Global average pooling, dropout 0.2, dense softmax with 3 outputs
- 2,261,827 parameters: 3,843 trainable and 2,257,984 non-trainable
- Adam, learning rate 0.001, sparse categorical cross-entropy
- Batch size 32, maximum 30 epochs
- Early stopping on validation loss, patience 5, restore best weights
- Augmentation off; class weighting and resampling off

Frozen pooled features were computed once per image and retained in memory for
head training. No preprocessed image or feature dataset was persisted.

## Results

| Rank | Variant | Macro F1 | Accuracy | Macro precision | Macro recall | Weighted F1 | Leaf spot recall | Best epoch | Epochs run |
| ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | P3 | 0.6627 | 0.7099 | 0.6880 | 0.6520 | 0.7036 | 0.44 | 13 | 18 |
| 2 | P2 | 0.6523 | 0.7068 | 0.6848 | 0.6410 | 0.6984 | 0.40 | 13 | 18 |
| 3 | P0 | 0.6396 | 0.7006 | 0.6870 | 0.6275 | 0.6893 | 0.36 | 11 | 16 |
| 4 | P1 | 0.6356 | 0.6944 | 0.7024 | 0.6187 | 0.6831 | 0.34 | 5 | 10 |

P3 is the D7 top candidate by validation macro F1. Its lead over P2 is 0.0104,
which is outside the predeclared close-candidate tolerance of 0.005. This result
is limited to this MobileNetV2 frozen-backbone protocol and one fixed seed; it
is not evidence of universal preprocessing superiority.

## Test Freeze And Data Safety

- Train unique paths accessed per run: 2,425
- Validation unique paths accessed per run: 324
- Test image bytes accessed per run: 0
- Raw metadata state changed: no
- Cleaned metadata state changed: no
- Split metadata state changed: no

Source-state verification compared path, size, and modified-time metadata so it
did not open frozen test image bytes. Each run also enforces and records the
train/validation-only path policy before image I/O.

## Verification

- Smoke test passed and is stored separately from full runs
- Full artifacts and saved-model load checks: PASS for P0-P3
- Unit tests: 15 passed, 0 failed
- Comparison input: validation metrics only

## Recommendation

Carry P3 forward as the D7 preprocessing candidate for the next controlled
model-comparison phase. Retain P2 as the nearest alternative. The relatively low
leaf spot recall remains an important limitation for later analysis. Do not use
the frozen test set until model and preprocessing choices are locked.
