# Plant Classifier Corrective Validation Evaluation

Thresholds: confidence >= `0.0`, margin >= `0.6936511993408203`.

| Scope | Coverage | Accepted accuracy | FAR among incorrect | Correct rejections | Wrongful rejections |
|---|---:|---:|---:|---:|---:|
| Overall | 2311/2340 (98.7607%) | 2311/2311 (100.0000%) | 0/7 (0.0000%) | 7/7 (100.0000%) | 22/2333 (0.9430%) |
| chrysanthemum | 231/233 (99.1416%) | 231/231 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 2/233 (0.8584%) |
| marigold | 72/73 (98.6301%) | 72/72 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 1/73 (1.3699%) |
| money_plant | 74/74 (100.0000%) | 74/74 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/74 (0.0000%) |
| rose | 1749/1775 (98.5352%) | 1749/1749 (100.0000%) | 0/7 (0.0000%) | 7/7 (100.0000%) | 19/1768 (1.0747%) |
| snake_plant | 86/86 (100.0000%) | 86/86 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/86 (0.0000%) |
| spider_plant | 99/99 (100.0000%) | 99/99 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/99 (0.0000%) |

## Limitations

- No unsupported/OOD dataset was evaluated; thresholds only filter low-confidence predictions among supported plants.
- This evaluation observed only 7 incorrect validation predictions (the supplied prior expectation was 7), so zero accepted validation errors cannot guarantee zero errors in production.
- This is not an external test set and may overlap with data used by one or more disease classifiers.
