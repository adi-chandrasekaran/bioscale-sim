from __future__ import annotations

from typing import Any, Dict

SOURCE_NAME = "ChEMBL"

LOCAL_DRUGS = [
    {
        "id": "CHEMBL941",
        "molecule_id": "CHEMBL941",
        "name": "Imatinib",
        "synonyms": ["Gleevec", "STI571"],
        "known_targets": ["ABL1", "KIT", "PDGFRA"],
        "mechanism_of_action": "Tyrosine kinase inhibition",
        "clinical_status": "approved in specific clinical contexts",
        "evidence_level": "local fallback; live ChEMBL not queried",
        "source": SOURCE_NAME,
    },
    {
        "id": "CHEMBL83",
        "molecule_id": "CHEMBL83",
        "name": "Aspirin",
        "synonyms": ["acetylsalicylic acid"],
        "known_targets": ["PTGS1", "PTGS2"],
        "mechanism_of_action": "Cyclooxygenase pathway modulation",
        "clinical_status": "approved in specific clinical contexts",
        "evidence_level": "local fallback; live ChEMBL not queried",
        "source": SOURCE_NAME,
    },
    {
        "id": "CHEMBL1201585",
        "molecule_id": "CHEMBL1201585",
        "name": "Pembrolizumab",
        "synonyms": ["Keytruda"],
        "known_targets": ["PDCD1"],
        "mechanism_of_action": "Immune checkpoint modulation",
        "clinical_status": "approved in specific clinical contexts",
        "evidence_level": "local fallback; live ChEMBL not queried",
        "source": SOURCE_NAME,
    },
]


def _matches(record: Dict[str, Any], query: str, target: str | None) -> bool:
    text = " ".join([record["name"], *record.get("synonyms", []), *record.get("known_targets", [])]).lower()
    query_ok = query.lower() in text
    target_ok = not target or target.lower() in text
    return query_ok and target_ok


def safe_search_drugs(query: str, target: str | None = None, limit: int = 10) -> Dict[str, Any]:
    results = [record for record in LOCAL_DRUGS if _matches(record, query, target)][:limit]
    return {
        "source": SOURCE_NAME,
        "available": False,
        "query": query,
        "target": target,
        "results": results,
        "limit": limit,
        "error": "ChEMBL live adapter unavailable; returned local fallback drug records when matched.",
    }


def safe_fetch_drug_evidence(drug: str) -> Dict[str, Any]:
    record = next((item for item in LOCAL_DRUGS if drug.lower() in item["name"].lower() or drug.lower() in [s.lower() for s in item.get("synonyms", [])]), None)
    return {
        "source": SOURCE_NAME,
        "available": False,
        "drug": drug,
        "record": record,
        "targets": record.get("known_targets", []) if record else [],
        "mechanism": record.get("mechanism_of_action", "") if record else "",
        "pharmacodynamics": {"ic50_ec50_kd": None, "note": "No live ChEMBL pharmacodynamic value available in this run."},
        "error": "ChEMBL live evidence unavailable; local fallback used if a record matched.",
    }
