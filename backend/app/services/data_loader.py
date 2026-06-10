from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "knowledge_base.json"


@lru_cache(maxsize=1)
def load_knowledge_base() -> Dict[str, Any]:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)
