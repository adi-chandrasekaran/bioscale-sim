"""Adapter package for external biological databases."""

from app.adapters.cache import get_cached, set_cached
from app.adapters.clinvar import safe_fetch_variant_evidence
from app.adapters.open_targets import safe_fetch_disease_targets
from app.adapters.reactome import safe_fetch_pathway_evidence
from app.adapters.uniprot import safe_fetch_protein_evidence

__all__ = [
    "get_cached",
    "set_cached",
    "safe_fetch_disease_targets",
    "safe_fetch_variant_evidence",
    "safe_fetch_protein_evidence",
    "safe_fetch_pathway_evidence",
]
