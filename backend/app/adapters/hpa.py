from __future__ import annotations

from typing import Any, Dict

SOURCE_NAME = "Human Protein Atlas"


def safe_fetch_tissue_expression(gene_symbol: str) -> Dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "available": False,
        "gene_symbol": gene_symbol,
        "tissue_expression": [],
        "cell_type_expression": [],
        "subcellular_location": [],
        "error": "HPA adapter stub: downloadable/API integration not yet implemented.",
    }
