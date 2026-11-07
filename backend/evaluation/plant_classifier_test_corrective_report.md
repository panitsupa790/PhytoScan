# Plant Classifier Corrective Test Evaluation

Thresholds: confidence >= `0.0`, margin >= `0.6936511993408203`.

| Scope | Coverage | Accepted accuracy | FAR among incorrect | Correct rejections | Wrongful rejections |
|---|---:|---:|---:|---:|---:|
| Overall | 1556/1580 (98.4810%) | 1555/1556 (99.9357%) | 1/7 (14.2857%) | 6/7 (85.7143%) | 18/1573 (1.1443%) |
| chrysanthemum | 157/161 (97.5155%) | 157/157 (100.0000%) | 0/1 (0.0000%) | 1/1 (100.0000%) | 3/160 (1.8750%) |
| marigold | 73/73 (100.0000%) | 73/73 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/73 (0.0000%) |
| money_plant | 49/49 (100.0000%) | 49/49 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/49 (0.0000%) |
| rose | 1155/1173 (98.4655%) | 1154/1155 (99.9134%) | 1/5 (20.0000%) | 4/5 (80.0000%) | 14/1168 (1.1986%) |
| snake_plant | 57/58 (98.2759%) | 57/57 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 1/58 (1.7241%) |
| spider_plant | 65/66 (98.4848%) | 65/65 (100.0000%) | 0/1 (0.0000%) | 1/1 (100.0000%) | 0/65 (0.0000%) |

## Limitations

- No unsupported/OOD dataset was evaluated; thresholds only filter low-confidence predictions among supported plants.
- This evaluation observed only 7 incorrect validation predictions (the supplied prior expectation was 7), so zero accepted validation errors cannot guarantee zero errors in production.
- This is not an external test set and may overlap with data used by one or more disease classifiers.
