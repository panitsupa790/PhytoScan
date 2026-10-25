# D9 Lite: EfficientNet-B0 Candidate Refinement

This experiment compares three controlled refinements against the frozen D8
EfficientNet-B0 + P3 checkpoint. Test images are blocked from the pipeline.

## Reproduce

Run from the repository root with the AI virtual environment:

```powershell
ai_model\.venv\Scripts\python.exe ai_model\experiments\eggplant_d9_refinement\run_experiment.py --run R1
ai_model\.venv\Scripts\python.exe ai_model\experiments\eggplant_d9_refinement\run_experiment.py --run R2
ai_model\.venv\Scripts\python.exe ai_model\experiments\eggplant_d9_refinement\run_experiment.py --run R3
ai_model\.venv\Scripts\python.exe ai_model\experiments\eggplant_d9_refinement\generate_comparison.py
ai_model\.venv\Scripts\python.exe ai_model\experiments\eggplant_d9_refinement\verify_source_state.py --verify
ai_model\.venv\Scripts\python.exe ai_model\experiments\eggplant_d9_refinement\validate_d9.py
```

The locked configuration is `ai_model/configs/eggplant_d9_refinement.json`.
Every run independently reloads the same R0 checkpoint. R3 augmentation is
online and train-only; no augmented dataset is written to disk.

`source_state_before.json` must be created with `--write-before` before rerunning
the experiment if a new source-data baseline is intentionally established.
