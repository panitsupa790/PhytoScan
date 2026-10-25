# PhytoScan Backend

FastAPI service for multi-plant disease classification. The production API
currently supports Rose and Sunflower. The user selects the plant; the service
does not attempt automatic plant classification.

## Architecture

- `app/data/plants.json` contains supported plant display metadata.
- `app/data/model_manifest.json` maps plant codes to model files, class order,
  input shape, preprocessing contract, and SHA-256.
- `app/data/diseases.json` contains disease display metadata separately from
  inference code.
- `app/services/model_registry.py` is the central plant/model registry.
- `app/services/plant_model_service.py` handles preprocessing, lazy model
  loading, model caching, validation, inference, and multi-image aggregation.

Adding a plant should require a model binary, one manifest entry, one plant
entry, and disease metadata; the route and inference implementation remain
unchanged.

## Models

Place the unchanged model binaries here:

```text
backend/app/models/rose-v1.keras
backend/app/models/sunflower-v1.keras
```

Both models expect RGB input resized directly to `224x224`, as `float32` values
in the `0..255` range. EfficientNet normalization is already inside each model,
so the backend does not divide inputs by 255. Class order is defined only in
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

Configuration is documented in `.env.example`. The default model manifest is
`app/data/model_manifest.json`.

## API

- `GET /health`
- `GET /api/v1/plants`
- `POST /api/v1/analyze`
- Swagger UI: `http://127.0.0.1:8000/docs`

Analysis uses multipart fields `plant_code` and one to three repeated `images`
files. Images must be JPG, JPEG, or PNG and are limited to 10 MB each by
default.

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/analyze" `
  -F "plant_code=rose" `
  -F "images=@C:\path\to\rose-leaf.jpg"
```

For multiple images, the model processes a single batch and the result uses the
mean class probabilities. Model-load failures return 503; inference failures
return 500; unsupported plants return 400.

The response keeps the aggregate `disease`, `symptoms`, `care`, and
`prevention` fields for backward compatibility and also returns
`image_results`. Each image result preserves upload order and contains its own
filename, disease, confidence, and metadata. These values come from the same
single-batch inference call; the service does not run a second prediction pass.

## Disease metadata status

The API schema supports `symptoms`, `care`, and `prevention`, but those fields
are intentionally empty for Rose and Sunflower until reviewed source data is
provided. The service does not invent treatment or disease guidance.

## Tests

```powershell
cd C:\phytoscan\backend
.\.venv\Scripts\python.exe -m pytest -q
```
