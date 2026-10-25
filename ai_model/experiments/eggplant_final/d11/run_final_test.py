from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


AI_MODEL_ROOT = Path(__file__).resolve().parents[3]
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from evaluation.d11_final_test import (  # noqa: E402
    evaluate_final_test,
    preflight,
    render_saved_confusion,
    verify_source_unchanged,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="D11 locked one-time final Test evaluation")
    parser.add_argument("action", choices=("preflight", "evaluate", "verify-source", "render"))
    args = parser.parse_args()
    if args.action == "preflight":
        result = preflight(write_artifacts=True)
    elif args.action == "evaluate":
        result = evaluate_final_test()
    elif args.action == "verify-source":
        result = verify_source_unchanged()
    else:
        result = render_saved_confusion()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
