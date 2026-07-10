from __future__ import annotations

from typing import Any, Dict

SOURCE_NAME = "DrugBank"


def safe_fetch_drugbank_evidence(drug: str) -> Dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "available": False,
        "drug": drug,
        "targets": [],
        "mechanisms": [],
        "error": "DrugBank requires licensing/API credentials; no DrugBank claims are shown.",
    }
