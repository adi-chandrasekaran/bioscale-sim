from __future__ import annotations

from typing import Any, Dict

SOURCE_NAME = "gnomAD"


def safe_fetch_variant_frequency(gene_symbol: str, mutation: str) -> Dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "available": False,
        "gene_symbol": gene_symbol,
        "mutation": mutation,
        "allele_frequency": None,
        "population_frequencies": {},
        "rarity": "unknown",
        "error": "gnomAD adapter stub: API/query integration not yet implemented.",
    }
