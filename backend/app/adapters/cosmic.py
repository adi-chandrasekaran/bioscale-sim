from __future__ import annotations

from typing import Any, Dict

SOURCE_NAME = "COSMIC"


def safe_fetch_somatic_mutation_evidence(gene_symbol: str, mutation: str) -> Dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "available": False,
        "gene_symbol": gene_symbol,
        "mutation": mutation,
        "results": [],
        "error": "COSMIC requires licensing; scraping is intentionally not implemented.",
    }
