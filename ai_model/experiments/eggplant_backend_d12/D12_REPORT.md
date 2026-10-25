# D12 Report: Eggplant Model Packaging and FastAPI Integration

## D12 Result

**PASS**

The locked Eggplant Disease Classifier v1 is integrated into the normal FastAPI
analyze path. D12 performed no training, fine-tuning, checkpoint selection, Test
optimization, or Flutter changes.

## Model Artifact

- Model: EfficientNet-B0, D9 R2
- Version: `eggplant-v1`
- Runtime checkpoint: `ai_model/experiments/eggplant_d9_refinement/R2_class_weight/best_model.keras`
- Checkpoint SHA-256: `ae0be68277300848eb4208c5184bf9c937cbe2ea9c8d5abc363eb38976135aa5`
- Locked config SHA-256: `5a7663db4f8c648fe06ce4d62206f7267946d357cedc6af73a6a7c35f432899b`
- Production manifest: `ai_model/models/eggplant/v1/model_manifest.json`
- Labels: `ai_model/models/eggplant/v1/labels.json`

The existing checkpoint is referenced directly. No duplicate model binary was
created under `ai_model/models`.

## Supported Scope

- Plant: Eggplant only
- Classes: `healthy`, `leaf_spot`, `mosaic_virus`
- Automatic Plant Classification: **NO**
- Hibiscus model: unavailable
- Snake plant model: unavailable

The API assumes inputs are eggplant images. Plant confidence `1.0` represents
this fixed service scope, not an automatic plant-classifier result.

## Inference Pipeline

Validated JPG/JPEG/PNG bytes
-> original shared P3 preprocessing
-> RGB 224x224 float32 in `[0,255]`
-> locked EfficientNet-B0 internal normalization
-> D9 R2 softmax
-> locked class mapping
-> disease catalog
-> existing API response schema

The backend imports `ai_model/preprocessing/eggplant.py`; no second preprocessing
algorithm was copied into the backend. Regression output matches locked P3
byte-for-byte for the same input.

## Multi-Image Aggregation

For one to three images, the service obtains one softmax vector per image,
calculates the arithmetic mean for each class, then returns
`argmax(mean probabilities)`. Confidence is the selected averaged probability.
No majority vote, confidence rejection, threshold tuning, ensemble, or test-time
augmentation is used.

## API

- Endpoint: `POST /api/v1/analyze`
- Request: multipart field `images`, repeated one to three times
- Formats: JPG, JPEG, PNG
- Response compatibility: unchanged `plant`, `disease`, `confidence`, `symptoms`, `care`, and `prevention` structure

Example from one Validation image:

```json
{
  "success": true,
  "image_count": 1,
  "plant": {"code": "eggplant", "name_en": "Eggplant", "confidence": 1.0},
  "disease": {"code": "healthy", "name_en": "Healthy Leaf", "confidence": 0.5248609781}
}
```

## Real Inference Verification

All examples used Validation images; D11 Test images were not used.

| Image | True class | Prediction | Confidence | H / LS / MV |
|---|---|---|---:|---|
| Healthy Leaf Image 1001.jpg | healthy | healthy | 0.5249 | 0.5249 / 0.0609 / 0.4143 |
| Leaf Spot Disease Image 129.jpg | leaf_spot | leaf_spot | 0.7202 | 0.1731 / 0.7202 / 0.1067 |
| Mosaic Virus Disease Image 1045.jpg | mosaic_virus | healthy | 0.6635 | 0.6635 / 0.0988 / 0.2376 |

The third result is retained as observed; it was not manually corrected or used
to tune the model. Three-image mean probabilities were 0.4538 / 0.2933 / 0.2529,
producing `healthy` with confidence 0.4538.

## Mock Removal

- Normal `POST /api/v1/analyze` path: **REAL**
- Mock fallback on model failure: **NO**
- Legacy mock service retained for isolated development compatibility: YES
- Former hard-coded confidences 0.94 / 0.84 observed in real HTTP responses: NO

Model failures return sanitized `MODEL_UNAVAILABLE` or `INFERENCE_FAILED`
responses without local paths, stack traces, or TensorFlow details.

## Performance

Measured on native Windows TensorFlow CPU:

- Model load: 1.24 seconds
- Direct first single-image inference: 0.45 seconds
- Direct subsequent single-image inference: approximately 0.34 seconds
- Direct three-image inference: 0.74 seconds
- First HTTP analyze including lazy load: 1.85 seconds
- Subsequent two-image HTTP request: 0.55 seconds
- Subsequent three-image HTTP request: 0.67 seconds
- Uvicorn working set after requests: approximately 658.6 MB
- Uvicorn private memory after requests: approximately 1,420.3 MB
- Process stability: PASS

The model loaded once and was reused. No D12 performance optimization was applied.

## Tests

- Backend tests: 31 passed, 0 failed
- AI regression tests: 39 passed, 0 failed
- D12 acceptance validator: 24 passed, 0 failed
- Real-model integration test: **PASS**
- Golden P3/model regression: **PASS**
- Real HTTP: health, docs, OpenAPI, and 1/2/3-image analyze all returned HTTP 200

## Data Safety

- Raw modified: FALSE
- Cleaned modified: FALSE
- Split modified: FALSE
- D11 results modified: FALSE
- Locked config modified: FALSE
- Locked checkpoint modified: FALSE
- D11 Test images used for D12 development: 0

## Training

- Training performed: **FALSE**
- Fine-tuning performed: **FALSE**
- Test-set tuning performed: **FALSE**
- Confidence threshold calibrated from Test: **FALSE**

## Git Status

- Commit: not performed
- Push: not performed
- Merge: not performed
- Auto-stage: not performed
- Model binary staged: FALSE
- Unrelated Flutter generated files: untouched

## Limitations

- Real AI supports Eggplant only.
- There is no automatic plant classifier.
- Hibiscus and snake plant models are not available.
- `mosaic_virus` is an image-based classification label, not laboratory confirmation.
- Final Eggplant v1 Test Accuracy is 0.7175 and Macro F1 is 0.6775.
- Disease guidance metadata requires domain-expert review before production agricultural use.
- CPU TensorFlow has a substantial memory footprint in this environment.

## Next Recommended Phase

D13: Flutter to Real AI end-to-end integration covering camera/gallery upload,
FastAPI, real Eggplant inference, and the dynamic result screen. D13 was not started.
