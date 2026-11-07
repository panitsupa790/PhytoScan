# Model Bundle Verification

All seven model artifacts and metadata valid: `True`.

| Model | SHA-256 | Class order | Input contract | Runtime bytes |
|---|---:|---:|---:|---:|
| plant_classifier | True | True | True | 17156154 |
| chrysanthemum | True | True | True | 33402583 |
| marigold | True | True | True | 33402578 |
| money_plant | True | True | True | 28977597 |
| rose | True | True | True | 33595897 |
| snake_plant | True | True | True | 28977551 |
| spider_plant | True | True | True | 28977593 |

The `.keras` files are intentionally ignored by Git. Deployment must provision all seven files and verify hashes against `model_manifest.json`.
