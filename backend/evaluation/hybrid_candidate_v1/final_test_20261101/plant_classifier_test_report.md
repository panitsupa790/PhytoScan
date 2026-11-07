# Hybrid Candidate Final Plant Classifier Test

Test purpose: evaluation only after threshold freeze; no threshold or model selection was performed.

- Raw accuracy: `1578/1580` (99.8734%)
- Macro precision: `99.4444%`
- Macro recall: `99.9716%`
- Macro F1: `99.7033%`
- Minimum per-class recall: `99.8295%`
- Frozen thresholds: confidence >= `0.0`, margin >= `0.34551629424095154`

| Scope | Coverage | Accepted accuracy | Accepted errors | Correct rejections | Wrongful rejections |
|---|---:|---:|---:|---:|---:|
| Overall | 1577/1580 (99.8101%) | 1576/1577 (99.9366%) | 1 | 1/2 (50.0000%) | 2/1578 (0.1267%) |

| True class | Support | Precision | Recall | F1 | Coverage |
|---|---:|---:|---:|---:|---:|
| chrysanthemum | 161 | 100.0000% | 100.0000% | 100.0000% | 161/161 (100.0000%) |
| marigold | 73 | 100.0000% | 100.0000% | 100.0000% | 73/73 (100.0000%) |
| money_plant | 49 | 100.0000% | 100.0000% | 100.0000% | 48/49 (97.9592%) |
| rose | 1173 | 100.0000% | 99.8295% | 99.9147% | 1171/1173 (99.8295%) |
| snake_plant | 58 | 96.6667% | 100.0000% | 98.3051% | 58/58 (100.0000%) |
| spider_plant | 66 | 100.0000% | 100.0000% | 100.0000% | 66/66 (100.0000%) |

## Limitations

- Unsupported/OOD detection: NOT VERIFIED.
- This Test set is not an independent external mobile-image test.
- Test results were not used to adjust thresholds or select a model.
