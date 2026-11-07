# Plant Classifier Hybrid_Candidate_Validation Evaluation

Thresholds: confidence >= `0.0`, margin >= `0.34551629424095154`.

| Scope | Coverage | Accepted accuracy | FAR among incorrect | Correct rejections | Wrongful rejections |
|---|---:|---:|---:|---:|---:|
| Overall | 2338/2340 (99.9145%) | 2338/2338 (100.0000%) | 0/1 (0.0000%) | 1/1 (100.0000%) | 1/2339 (0.0428%) |
| chrysanthemum | 233/233 (100.0000%) | 233/233 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/233 (0.0000%) |
| marigold | 73/73 (100.0000%) | 73/73 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/73 (0.0000%) |
| money_plant | 73/74 (98.6486%) | 73/73 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 1/74 (1.3514%) |
| rose | 1774/1775 (99.9437%) | 1774/1774 (100.0000%) | 0/1 (0.0000%) | 1/1 (100.0000%) | 0/1774 (0.0000%) |
| snake_plant | 86/86 (100.0000%) | 86/86 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/86 (0.0000%) |
| spider_plant | 99/99 (100.0000%) | 99/99 (100.0000%) | 0/0 (N/A) | 0/0 (N/A) | 0/99 (0.0000%) |

## Limitations

- No unsupported/OOD dataset was evaluated; thresholds only filter low-confidence predictions among supported plants.
- This evaluation observed only 1 incorrect validation predictions (the supplied prior expectation was 7), so zero accepted validation errors cannot guarantee zero errors in production.
- This is not an external test set and may overlap with data used by one or more disease classifiers.
