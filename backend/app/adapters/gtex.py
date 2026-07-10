from __future__ import annotations

from typing import Any, Dict

SOURCE_NAME = "GTEx"


def safe_fetch_gene_expression(gene_symbol: str) -> Dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "available": False,
        "gene_symbol": gene_symbol,
        "tissue_expression": [],
        "error": "GTEx adapter stub: no simple live API wired yet.",
    }
