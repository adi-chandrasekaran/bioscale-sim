from __future__ import annotations

from typing import Any, Dict

SOURCE_NAME = "cBioPortal"


def safe_search_cancer_studies(query: str) -> Dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "available": False,
        "query": query,
        "results": [],
        "error": "cBioPortal adapter stub: cohort integration not yet implemented.",
    }
