from __future__ import annotations

from typing import Any, Dict

SOURCE_NAME = "CIViC"


def safe_fetch_variant_evidence(gene_symbol: str, mutation: str) -> Dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "available": False,
        "gene_symbol": gene_symbol,
        "mutation": mutation,
        "evidence_items": [],
        "therapy_associations": [],
        "error": "CIViC adapter stub: cancer variant evidence integration not yet implemented.",
    }
