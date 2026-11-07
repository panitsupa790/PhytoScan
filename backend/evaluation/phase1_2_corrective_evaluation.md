# Phase 1.2 — Threshold Recalibration & Corrective Evaluation

## Result

Phase 1.2 completed without changing model weights, datasets, splits, or Flutter/Mobile.
The historical Pillow reports remain unchanged. The active automatic router now
requires the corrective frozen config and its SHA-bound completion receipt.

## Frozen configuration

- Selection source: Validation only (2,340 images)
- Model SHA-256: `5585bb91835006003e6f052c58465d84fc0d9ac6e37227d842a28d18f3991165`
- Frozen config SHA-256: `96ebd02a1ed29d7f78d439903c5cd439260aee9a3bae3dfefe60a2ac240446c7`
- `MIN_CONFIDENCE`: `0.0`
- `MIN_MARGIN`: `0.6936511993408203`
- Input: TensorFlow `decode_image(channels=3, expand_animations=False)`, cast to
  `float32`, TensorFlow bilinear resize to `224x224`, values in `0..255`, no
  external normalization.
- Accept rule: confidence and margin are both greater than or equal to their thresholds.

Exact observed-boundary candidates used `0.0`, `nextafter(observed_value, +inf)`
in inference `float32`, and `1.0`. Selection minimized Accepted Errors, then
maximized Coverage, required at least one accepted sample in every true class,
and broke ties by lower confidence threshold then lower margin threshold. The
winning pair achieved zero Accepted Errors and accepted 231, 72, 74, 1,749, 86,
and 99 Validation samples respectively across the six classes.

## Validation metrics

| True plant | Coverage | Accepted accuracy | Accepted errors / accepted | FAR among incorrect | Correct rejections | Wrongful rejections |
|---|---:|---:|---:|---:|---:|---:|
| Overall | 2311/2340 (98.7607%) | 2311/2311 (100.0000%) | 0/2311 (0.0000%) | 0/7 (0.0000%) | 7/7 (100.0000%) | 22/2333 (0.9430%) |
| chrysanthemum | 231/233 (99.1416%) | 231/231 (100.0000%) | 0/231 (0.0000%) | 0/0 (N/A) | 0/0 (N/A) | 2/233 (0.8584%) |
| marigold | 72/73 (98.6301%) | 72/72 (100.0000%) | 0/72 (0.0000%) | 0/0 (N/A) | 0/0 (N/A) | 1/73 (1.3699%) |
| money_plant | 74/74 (100.0000%) | 74/74 (100.0000%) | 0/74 (0.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/74 (0.0000%) |
| rose | 1749/1775 (98.5352%) | 1749/1749 (100.0000%) | 0/1749 (0.0000%) | 0/7 (0.0000%) | 7/7 (100.0000%) | 19/1768 (1.0747%) |
| snake_plant | 86/86 (100.0000%) | 86/86 (100.0000%) | 0/86 (0.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/86 (0.0000%) |
| spider_plant | 99/99 (100.0000%) | 99/99 (100.0000%) | 0/99 (0.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/99 (0.0000%) |

The base classifier made 7/2,340 incorrect top-1 predictions on Validation.

## Corrective Test metrics

The Test set (1,580 images) was opened once only after the config was frozen.
No candidate construction, threshold selection, or threshold adjustment used Test.

| True plant | Coverage | Accepted accuracy | Accepted errors / accepted | FAR among incorrect | Correct rejections | Wrongful rejections |
|---|---:|---:|---:|---:|---:|---:|
| Overall | 1556/1580 (98.4810%) | 1555/1556 (99.9357%) | 1/1556 (0.0643%) | 1/7 (14.2857%) | 6/7 (85.7143%) | 18/1573 (1.1443%) |
| chrysanthemum | 157/161 (97.5155%) | 157/157 (100.0000%) | 0/157 (0.0000%) | 0/1 (0.0000%) | 1/1 (100.0000%) | 3/160 (1.8750%) |
| marigold | 73/73 (100.0000%) | 73/73 (100.0000%) | 0/73 (0.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/73 (0.0000%) |
| money_plant | 49/49 (100.0000%) | 49/49 (100.0000%) | 0/49 (0.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/49 (0.0000%) |
| rose | 1155/1173 (98.4655%) | 1154/1155 (99.9134%) | 1/1155 (0.0866%) | 1/5 (20.0000%) | 4/5 (80.0000%) | 14/1168 (1.1986%) |
| snake_plant | 57/58 (98.2759%) | 57/57 (100.0000%) | 0/57 (0.0000%) | 0/0 (N/A) | 0/0 (N/A) | 1/58 (1.7241%) |
| spider_plant | 65/66 (98.4848%) | 65/65 (100.0000%) | 0/65 (0.0000%) | 0/1 (0.0000%) | 1/1 (100.0000%) | 0/65 (0.0000%) |

The base classifier made 7/1,580 incorrect top-1 predictions on Test.

## Historical versus corrective

| Split | Pipeline / threshold | Raw errors | Accepted | Accepted errors | Coverage | Accepted accuracy | FAR |
|---|---|---:|---:|---:|---:|---:|---:|
| Validation historical | Pillow / margin 0.4026440382 | 2 | 2330 | 0 | 99.5726% | 100.0000% | 0/2 (0.0000%) |
| Validation corrective | TensorFlow / margin 0.6936511993 | 7 | 2311 | 0 | 98.7607% | 100.0000% | 0/7 (0.0000%) |
| Test historical | Pillow / margin 0.4026440382 | 3 | 1576 | 1 | 99.7468% | 99.9365% | 1/3 (33.3333%) |
| Test corrective | TensorFlow / margin 0.6936511993 | 7 | 1556 | 1 | 98.4810% | 99.9357% | 1/7 (14.2857%) |

The raw error difference is caused by the previously audited Pillow versus
TensorFlow decode/resize mismatch, not by a different model, class mapping,
manifest order, or label/prediction pairing. FAR percentages are not directly
comparable without their denominators because the number of incorrect top-1
predictions changed.

## Integrity, routing, and tests

- Corrective Test completion receipt status: `corrective_test_completed`.
- Corrective Test report SHA-256: `90ae279707f07c34df557a0dbcbafee3ee6e5f866978bf0bff4906a4ab20ab90`.
- Corrective Test row predictions SHA-256: `beb5954f184dacc1cbd7e6e4042c5008fb62b63ee15bb2f9194151e946310ce6`.
- Row-level Validation and Test CSVs contain path, group ID, true/predicted label,
  confidence, margin, correctness, and accepted/rejected decision.
- Historical Validation/Test report SHA-256 values remain
  `db1877caae0e513901af515fded49c82f499be97780a684709620d2f0c3cdbf2`
  and `384a7a3c10989f1f3b6a316d9c7cd9b064e6404df979bfdd5b5e35704ae321ab`.
- Runtime automatic routing is enabled only when model metadata, input contract,
  frozen config SHA-256, receipt, Test report, and Test prediction CSV all match.
  Any mismatch fails closed. Low-confidence/margin and mixed-plant uploads return
  `manual_confirmation_required` without invoking a disease classifier.
- A user-supplied `plant_code` is restricted to the six active registry entries.
- Model bundle read-only recheck: all seven active model files match source and
  manifest SHA-256, class order, and input metadata. `.keras` remains Git-ignored
  and must be provisioned and verified during deployment.
- Automated tests: `63 passed in 20.66s`.
- Flutter/Mobile diff: none.

## Limitations and Phase 2 gate

- Only seven Validation errors were available. Zero Accepted Errors on Validation
  does not establish zero-error production behavior.
- Corrective Test contains one accepted incorrect prediction; the threshold was
  not changed after observing it.
- No unsupported/OOD or non-leaf dataset was evaluated. These thresholds do not
  claim unsupported-plant detection.
- Validation/Test are not external mobile-photo test sets and may overlap data
  used by one or more disease classifiers.
- Automatic classification should retain manual plant confirmation as the safe
  fallback. Deployment must provision all seven ignored `.keras` files and verify
  their manifest hashes.

Phase 1.2 backend evidence is complete and ready for review. Phase 2 Flutter
integration has not started.
