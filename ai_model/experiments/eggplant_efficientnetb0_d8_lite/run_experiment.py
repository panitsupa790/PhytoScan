from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


AI_MODEL_ROOT = Path(__file__).resolve().parents[2]
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from training.d8_efficientnetb0 import load_training_config, run_variant  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one D8 Lite EfficientNetB0 experiment")
    parser.add_argument("--variant", required=True, choices=("P0", "P3"))
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    config = load_training_config()
    root = Path(__file__).resolve().parent
    output = root / ("smoke" if args.smoke else "runs") / args.variant
    result = run_variant(args.variant, config, output, smoke=args.smoke)
    print(json.dumps({"output": str(output), **result["metrics"], "access": result["access"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
