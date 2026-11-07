# PhytoScan Backend

FastAPI service with a two-stage plant and disease classification pipeline.
The active registry supports Chrysanthemum, Marigold, Money Plant, Rose,
Snake Plant, and Spider Plant. Sunflower is not active.

## Architecture

- `app/data/plants.json` contains supported plant display metadata.
- `app/data/model_manifest.json` defines the plant classifier and six disease
  classifiers, including class order, preprocessing contract, and SHA-256.
- `app/data/plant_classifier_evaluation.json` preserves the historical Pillow-based
  threshold configuration.
- `app/data/plant_classifier_evaluation_corrective.json` is the active threshold
  configuration frozen from Validation with the TensorFlow input contract.
- `app/data/plant_classifier_corrective_test_receipt.json` proves the corrective
  Test completed against that exact frozen config before automatic routing opens.
- `app/data/diseases.json` contains disease display metadata separately from
  inference code.
- `app/services/model_registry.py` validates the central model registry.
- `app/services/plant_classifier_service.py` classifies every uploaded image.
- `app/services/analysis_router.py` enforces thresholds and routes accepted or
  manually confirmed plants to the corresponding disease classifier.
- `app/services/plant_model_service.py` performs disease inference, caching,
  and multi-image probability aggregation.

## Models

Place the unchanged model binaries under `app/models/` using the filenames
declared in the manifest:

```text
plant-classifier-v1.keras
chrysanthemum-v1.keras
marigold-v1.keras
money-plant-v1.keras
rose-v1.keras
snake-plant-v1.keras
spider-plant-v1.keras
```

All models expect RGB input resized directly to `224x224`, as `float32` values
in the `0..255` range. EfficientNet rescaling is inside each model, so the
backend does not divide inputs by 255. Class order is defined only in
`app/data/model_manifest.json` and must not be reordered.

## Setup and run

Requirements: Python 3.12 and PowerShell.

```powershell
cd C:\phytoscan\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API

- `GET /health`
- `GET /api/v1/plants`
- `POST /api/v1/analyze`
- Swagger UI: `http://127.0.0.1:8000/docs`

Analysis accepts one to three repeated `images` files. `plant_code` is optional:
omit it for automatic plant classification, or provide it after the user has
manually confirmed the plant. Images must be JPG, JPEG, or PNG and are limited
to 10 MB each by default.

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/analyze" `
  -F "images=@C:\path\to\rose-leaf.jpg"
```

Automatic routing requires every image to predict the same plant and every
image to meet both frozen thresholds. Otherwise the response status is
`manual_confirmation_required`, and no disease model is called. Resubmit with
`plant_code` to record manual confirmation and continue disease analysis.

Automatic routing uses the completed corrective evaluation. It fails closed
with 503 if the model SHA-256, class order, preprocessing contract, frozen-config
SHA-256, Test receipt, Test report, or row-level prediction checksum does not
match. Manually confirmed `plant_code` requests remain available for supported
plants.

The completed response retains the aggregate disease and metadata fields for
backward compatibility and includes one `image_results` entry per upload.
Model-load failures return 503, inference failures return 500, and unsupported
manually confirmed plant codes return 400.

## Evaluation

The historical Pillow thresholds remain unchanged at `MIN_CONFIDENCE=0.0` and
`MIN_MARGIN=0.4026440382003784`. A parity audit invalidated them for the corrected
runtime. Phase 1.2 selected the active thresholds from Validation only using the
Notebook-compatible TensorFlow pipeline: `MIN_CONFIDENCE=0.0` and
`MIN_MARGIN=0.6936511993408203`. See
`evaluation/phase1_2_corrective_evaluation.md`.

The selection and Test commands remain deliberately separate, and the Test
command refuses to overwrite an existing Test report:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_plant_classifier.py select-validation
.\.venv\Scripts\python.exe scripts\evaluate_plant_classifier.py evaluate-test
.\.venv\Scripts\python.exe scripts\evaluate_plant_classifier.py select-corrective-validation
.\.venv\Scripts\python.exe scripts\evaluate_plant_classifier.py evaluate-corrective-test
```

Both historical and corrective Test artifacts already exist. The commands refuse
to repeat or overwrite them. Any future protocol must write a new artifact set;
Test results must never select or adjust a threshold. There is no unsupported/OOD
dataset yet, so thresholds only filter low-confidence predictions among supported
plants.

## Disease metadata status

The API schema supports `symptoms`, `care`, and `prevention`, but these fields
are intentionally empty for active production models until reviewed source
data is provided. The service does not invent treatment or disease guidance.

## Tests

```powershell
cd C:\phytoscan\backend
.\.venv\Scripts\python.exe -m pytest -q
```
