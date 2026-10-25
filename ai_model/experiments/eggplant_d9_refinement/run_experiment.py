from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


AI_MODEL_ROOT = Path(__file__).resolve().parents[2]
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from training.d9_refinement import load_training_config, run_experiment  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one D9 EfficientNet-B0 refinement experiment")
    parser.add_argument("--run", required=True, choices=("R1", "R2", "R3"))
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    config = load_training_config()
    root = Path(__file__).resolve().parent
    directory = config["runs"][args.run]["directory"]
    output = root / ("smoke" if args.smoke else "") / directory
    result = run_experiment(args.run, config, output, smoke=args.smoke)
    print(json.dumps({"output": str(output), **result["metrics"], "access": result["access"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
