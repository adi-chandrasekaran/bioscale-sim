from __future__ import annotations

from typing import Any, Dict

SOURCE_NAME = "PharmGKB"


def safe_fetch_pharmacogenomic_evidence(gene_symbol: str, mutation: str) -> Dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "available": False,
        "gene_symbol": gene_symbol,
        "mutation": mutation,
        "drug_response_evidence": [],
        "error": "PharmGKB adapter stub: access/licensing workflow not yet wired.",
    }
