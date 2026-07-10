from __future__ import annotations

from typing import Any, Dict

from app.adapters.chembl import safe_fetch_drug_evidence, safe_search_drugs
from app.adapters.civic import safe_fetch_variant_evidence
from app.adapters.drugbank_stub import safe_fetch_drugbank_evidence
from app.adapters.pharmgkb import safe_fetch_pharmacogenomic_evidence
from app.adapters.rxnorm import safe_normalize_drug_name


def search_intervention_drugs(query: str, target: str | None = None, limit: int = 10) -> Dict[str, Any]:
    return safe_search_drugs(query, target=target, limit=limit)


def fetch_intervention_evidence(drug: str, gene: str = "", mutation: str = "") -> Dict[str, Any]:
    rxnorm = safe_normalize_drug_name(drug)
    normalized = rxnorm.get("normalized_name") or drug
    chembl = safe_fetch_drug_evidence(str(normalized))
    civic = safe_fetch_variant_evidence(gene, mutation) if gene or mutation else {"source": "CIViC", "available": False, "therapy_associations": []}
    drugbank = safe_fetch_drugbank_evidence(str(normalized))
    pharmgkb = safe_fetch_pharmacogenomic_evidence(gene, mutation) if gene or mutation else {"source": "PharmGKB", "available": False, "drug_response_evidence": []}
    sources = [rxnorm, chembl, civic, drugbank, pharmgkb]
    record = chembl.get("record") or {}
    return {
        "drug": drug,
        "normalized_drug": normalized,
        "available": any(source.get("available") for source in sources),
        "source_summaries": sources,
        "mechanism": record.get("mechanism_of_action") or chembl.get("mechanism") or "No evidence-backed mechanism found; simulator will use generic mechanism-based assumptions.",
        "known_targets": record.get("known_targets") or chembl.get("targets") or [],
        "clinical_status": record.get("clinical_status") or "unknown",
        "evidence_level": record.get("evidence_level") or "simulator assumption",
        "pharmacodynamics": chembl.get("pharmacodynamics", {}),
        "raw": {"rxnorm": rxnorm, "chembl": chembl, "civic": civic, "drugbank": drugbank, "pharmgkb": pharmgkb},
    }
