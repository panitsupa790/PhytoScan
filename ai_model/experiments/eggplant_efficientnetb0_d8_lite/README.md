# D8 Lite EfficientNet-B0 Controlled Experiment

This experiment compares D6 P0 and P3 with an ImageNet-pretrained, frozen
EfficientNet-B0 backbone. All training settings are identical between runs.
Augmentation, class balancing, resampling, and fine-tuning are disabled.

TensorFlow 2.21 was inspected directly. Its EfficientNet `preprocess_input` is
an identity compatibility function, while EfficientNet-B0 contains internal
`Rescaling(1/255)` and `Normalization` layers. The pipeline therefore supplies
D6 RGB images as float32 values in the original [0, 255] range. MobileNetV2's
[-1, 1] normalization is not used.

Only train and validation records are loadable. Every unique image path opened
is audited, and test split requests are rejected before image I/O. Frozen pooled
features are cached in memory; no transformed image or feature dataset is saved.

The smoke output is isolated under `smoke/`. Full P0/P3 outputs are under
`runs/`, and the combined D7/D8 validation-only comparison is under
`comparison/`. The test set remains frozen for a later final evaluation.
