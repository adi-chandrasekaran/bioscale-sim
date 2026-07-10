from __future__ import annotations

from typing import Any, Dict

SOURCE_NAME = "RxNorm"


def safe_normalize_drug_name(drug: str) -> Dict[str, Any]:
    normalized = {
        "gleevec": "imatinib",
        "keytruda": "pembrolizumab",
        "acetylsalicylic acid": "aspirin",
    }.get(drug.lower(), drug)
    return {
        "source": SOURCE_NAME,
        "available": False,
        "query": drug,
        "normalized_name": normalized,
        "rxnorm_id": None,
        "error": "RxNorm live normalization unavailable; local synonym fallback used.",
    }
