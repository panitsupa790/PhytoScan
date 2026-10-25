from __future__ import annotations

import json
import sys
from pathlib import Path


AI_MODEL_ROOT = Path(__file__).resolve().parents[2]
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from finalization.d10_lock import write_lock  # noqa: E402


if __name__ == "__main__":
    print(json.dumps(write_lock(), indent=2))
