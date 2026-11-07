# Plant Classifier Test Evaluation

Thresholds: confidence >= `0.0`, margin >= `0.4026440382003784`.

| Scope | Coverage | Accepted accuracy | FAR among incorrect | Correct rejections | Wrongful rejections |
|---|---:|---:|---:|---:|---:|
| Overall | 1576/1580 (99.7468%) | 1575/1576 (99.9365%) | 1/3 (33.3333%) | 2/3 (66.6667%) | 2/1577 (0.1268%) |
| chrysanthemum | 161/161 (100.0000%) | 161/161 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/161 (0.0000%) |
| marigold | 73/73 (100.0000%) | 73/73 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/73 (0.0000%) |
| money_plant | 49/49 (100.0000%) | 49/49 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/49 (0.0000%) |
| rose | 1170/1173 (99.7442%) | 1169/1170 (99.9145%) | 1/2 (50.0000%) | 1/2 (50.0000%) | 2/1171 (0.1708%) |
| snake_plant | 58/58 (100.0000%) | 58/58 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/58 (0.0000%) |
| spider_plant | 65/66 (98.4848%) | 65/65 (100.0000%) | 0/1 (0.0000%) | 1/1 (100.0000%) | 0/65 (0.0000%) |

## Limitations

- No unsupported/OOD dataset was evaluated; thresholds only filter low-confidence predictions among supported plants.
- This evaluation observed only 2 incorrect validation predictions (the supplied prior expectation was 7), so zero accepted validation errors cannot guarantee zero errors in production.
- This is not an external test set and may overlap with data used by one or more disease classifiers.
