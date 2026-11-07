# Plant Classifier Validation_Frozen_Threshold_After_Preprocessing_Fix Evaluation

Thresholds: confidence >= `0.0`, margin >= `0.4026440382003784`.

| Scope | Coverage | Accepted accuracy | FAR among incorrect | Correct rejections | Wrongful rejections |
|---|---:|---:|---:|---:|---:|
| Overall | 2329/2340 (99.5299%) | 2325/2329 (99.8283%) | 4/7 (57.1429%) | 3/7 (42.8571%) | 8/2333 (0.3429%) |
| chrysanthemum | 233/233 (100.0000%) | 233/233 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/233 (0.0000%) |
| marigold | 73/73 (100.0000%) | 73/73 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/73 (0.0000%) |
| money_plant | 74/74 (100.0000%) | 74/74 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/74 (0.0000%) |
| rose | 1764/1775 (99.3803%) | 1760/1764 (99.7732%) | 4/7 (57.1429%) | 3/7 (42.8571%) | 8/1768 (0.4525%) |
| snake_plant | 86/86 (100.0000%) | 86/86 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/86 (0.0000%) |
| spider_plant | 99/99 (100.0000%) | 99/99 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/99 (0.0000%) |

## Limitations

- No unsupported/OOD dataset was evaluated; thresholds only filter low-confidence predictions among supported plants.
- This evaluation observed only 7 incorrect validation predictions (the supplied prior expectation was 7), so zero accepted validation errors cannot guarantee zero errors in production.
- This is not an external test set and may overlap with data used by one or more disease classifiers.
