from __future__ import annotations

from typing import Any, Dict

SOURCE_NAME = "MONDO/HPO"


def safe_search_phenotypes(query: str, limit: int = 10) -> Dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "available": False,
        "query": query,
        "results": [],
        "limit": limit,
        "error": "MONDO/HPO adapter stub: ontology search not yet implemented.",
    }
