from __future__ import annotations

from typing import Any, Dict

SOURCE_NAME = "NCI GDC"


def safe_search_projects(query: str) -> Dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "available": False,
        "query": query,
        "results": [],
        "error": "GDC adapter stub: public cohort integration not yet implemented.",
    }
