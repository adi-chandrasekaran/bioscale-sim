from __future__ import annotations

from typing import Any, Dict

SOURCE_NAME = "ClinGen"


def safe_fetch_gene_disease_validity(gene_symbol: str, disease_id: str | None = None) -> Dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "available": False,
        "gene_symbol": gene_symbol,
        "disease_id": disease_id,
        "validity": "unknown",
        "dosage_sensitivity": "unknown",
        "error": "ClinGen adapter stub: gene-disease validity integration not yet implemented.",
    }
