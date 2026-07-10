from __future__ import annotations

from typing import Any, Dict

SOURCE_NAME = "OMIM"


def safe_fetch_mendelian_evidence(gene_symbol: str) -> Dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "available": False,
        "gene_symbol": gene_symbol,
        "results": [],
        "error": "OMIM requires API/licensing; scraping is intentionally not implemented.",
    }
