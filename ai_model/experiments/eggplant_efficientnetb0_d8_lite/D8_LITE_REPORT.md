# D8 Lite Result

PASS

EfficientNet-B0 P0 and P3 completed under one controlled configuration. Model
selection evidence in this report comes from validation only. Test image bytes
were not accessed.

## Environment And Normalization

- Python 3.12.4; TensorFlow 2.21.0 / Keras 3.15.1
- Device: CPU
- Input: RGB float32, 224x224x3, value range [0, 255]
- TensorFlow 2.21 EfficientNet `preprocess_input`: identity compatibility function
- EfficientNet-B0 internal preprocessing: Rescaling(1/255) and Normalization
- MobileNetV2 [-1, 1] normalization was not used

## Controlled Configuration

- ImageNet pretrained EfficientNet-B0, `include_top=false`, frozen backbone
- Global average pooling, dropout 0.2, three-class softmax
- Adam, learning rate 0.001, sparse categorical cross-entropy
- Batch size 32, maximum 30 epochs
- Early stopping on validation loss, patience 5, restore best weights
- Seed 42
- Augmentation, class weights, over/under-sampling, and fine-tuning: off
- Parameters: 4,053,414 total; 3,843 trainable; 4,049,571 non-trainable

Frozen pooled features were cached in memory. No transformed image or feature
dataset was written to disk.

## Model Comparison

| Model | Preprocess | Val Accuracy | Macro F1 | Leaf Spot Recall | Best Epoch |
| :--- | :--- | ---: | ---: | ---: | ---: |
| MobileNetV2 | P0 | 0.7006 | 0.6396 | 0.36 | 11 |
| MobileNetV2 | P3 | 0.7099 | 0.6627 | 0.44 | 13 |
| EfficientNet-B0 | P0 | 0.7191 | 0.6748 | 0.42 | 15 |
| EfficientNet-B0 | P3 | **0.7407** | **0.7040** | **0.46** | 15 |

## EfficientNet P0 Vs P3

P3 improved validation macro F1 by 0.0292, accuracy by 0.0216, and leaf_spot
recall by 0.04 relative to P0. Both runs stopped after 20 epochs, with their
lowest validation loss at epoch 15.

EfficientNet P0 metrics: macro precision 0.7337, macro recall 0.6551, macro F1
0.6748, weighted F1 0.7115. EfficientNet P3 metrics: macro precision 0.7696,
macro recall 0.6806, macro F1 0.7040, weighted F1 0.7347.

P3 per-class precision / recall / F1:

| Class | Precision | Recall | F1 | Support |
| :--- | ---: | ---: | ---: | ---: |
| healthy | 0.6857 | 0.8633 | 0.7643 | 139 |
| leaf_spot | 0.8214 | 0.4600 | 0.5897 | 50 |
| mosaic_virus | 0.8017 | 0.7185 | 0.7578 | 135 |

## MobileNet Vs EfficientNet

At P0, EfficientNet-B0 improved macro F1 by 0.0352 over MobileNetV2. At P3,
EfficientNet-B0 improved macro F1 by 0.0412 and leaf_spot recall by 0.02.

EfficientNet-B0 with P3 is the top validation candidate among the four rows.
This is not a final model decision because the test set remains unopened.

## P2 Tie-Breaker

P2 is not recommended for this D8 Lite round. The EfficientNet P0/P3 macro F1
difference is greater than 0.005, and P3 leaf_spot recall is higher than P0.
P2 was not trained.

## Test Freeze And Data Safety

- Train unique paths accessed per full run: 2,425
- Validation unique paths accessed per full run: 324
- Test image bytes accessed per run: 0
- Raw, cleaned, and split source metadata state: unchanged

## Verification

- Smoke test: passed and isolated from full runs
- Full P0/P3 models and artifacts: passed validation
- Saved models: loadable, input 224x224x3, output 3 classes
- Unit tests: 19 passed, 0 failed
- Commit, push, merge, and auto-stage: not performed
