# Plant Classifier Validation Evaluation

Thresholds: confidence >= `0.0`, margin >= `0.4026440382003784`.

| Scope | Coverage | Accepted accuracy | FAR among incorrect | Correct rejections | Wrongful rejections |
|---|---:|---:|---:|---:|---:|
| Overall | 2330/2340 (99.5726%) | 2330/2330 (100.0000%) | 0/2 (0.0000%) | 2/2 (100.0000%) | 8/2338 (0.3422%) |
| chrysanthemum | 233/233 (100.0000%) | 233/233 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/233 (0.0000%) |
| marigold | 73/73 (100.0000%) | 73/73 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/73 (0.0000%) |
| money_plant | 74/74 (100.0000%) | 74/74 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/74 (0.0000%) |
| rose | 1766/1775 (99.4930%) | 1766/1766 (100.0000%) | 0/2 (0.0000%) | 2/2 (100.0000%) | 7/1773 (0.3948%) |
| snake_plant | 86/86 (100.0000%) | 86/86 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/86 (0.0000%) |
| spider_plant | 98/99 (98.9899%) | 98/98 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 1/99 (1.0101%) |

## Limitations

- No unsupported/OOD dataset was evaluated; thresholds only filter low-confidence predictions among supported plants.
- This evaluation observed only 2 incorrect validation predictions (the supplied prior expectation was 7), so zero accepted validation errors cannot guarantee zero errors in production.
- This is not an external test set and may overlap with data used by one or more disease classifiers.
