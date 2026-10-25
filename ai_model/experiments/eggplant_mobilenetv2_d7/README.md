# D7 MobileNetV2 Controlled Preprocessing Experiments

This experiment compares D6 preprocessing variants P0-P3 while holding the
MobileNetV2 architecture and all training settings constant. The ImageNet
backbone is frozen. A global-average-pooling, dropout, and three-class softmax
head is trained with Adam and sparse categorical cross-entropy.

Because the backbone is frozen, each run computes its pooled MobileNetV2
features once and caches those features in memory while the classification head
is trained. This is equivalent to repeating the unchanged frozen forward pass
at every epoch, avoids unnecessary CPU work, and does not persist transformed
images or feature datasets.

The deterministic D6 preprocessing operation is applied in memory first. The
MobileNetV2 `preprocess_input` normalization is then applied exactly once in
the model input pipeline. No transformed dataset copy is written.

Only train and validation rows are selected from the D5 manifest. The loader
rejects test split requests before image I/O and records every unique source
path opened. Test image bytes must remain zero in every access audit.

Augmentation, class weighting, over-sampling, and under-sampling are disabled.
The primary selection metric is validation macro F1. Accuracy, macro precision,
macro recall, weighted F1, per-class metrics, and validation confusion matrices
are supporting evidence. Candidates within 0.005 macro F1 of the top score are
reported as close; this is an operational tolerance, not a significance test.

Run the smoke check before full experiments:

```powershell
ai_model\.venv\Scripts\python.exe ai_model\experiments\eggplant_mobilenetv2_d7\run_experiment.py --variant P0 --smoke
```

Full runs use the same command without `--smoke`, once for each P0-P3. Generate
the validation-only comparison after all four full runs:

```powershell
ai_model\.venv\Scripts\python.exe ai_model\experiments\eggplant_mobilenetv2_d7\compare_results.py
```

The frozen test set is reserved for final evaluation after preprocessing and
model choices are locked in a later phase.
