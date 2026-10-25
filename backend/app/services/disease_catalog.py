# ./backend/app/services/disease_catalog.py

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "diseases.json"


@lru_cache(maxsize=1)
def load_disease_catalog() -> dict[str, dict[str, dict[str, Any]]]:
    with DATA_FILE.open(encoding="utf-8") as data_file:
        return json.load(data_file)


def get_disease_record(plant: str, disease: str) -> dict[str, Any]:
    try:
        return load_disease_catalog()[plant][disease]
    except KeyError as error:
        raise ValueError(f"Missing disease metadata for {plant}/{disease}") from error
