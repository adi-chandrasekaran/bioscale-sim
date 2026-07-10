from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from app.adapters.cache import get_cached, set_cached

SOURCE_NAME = "AlphaFold DB"
API_BASE = "https://alphafold.ebi.ac.uk/api/prediction"
FILES_BASE = "https://alphafold.ebi.ac.uk/files"
TIMEOUT_SECONDS = 20


def _model_prefix(uniprot_accession: str) -> str:
    return f"AF-{uniprot_accession}-F1"


def get_pdb_url(uniprot_accession: str) -> str:
    return f"{FILES_BASE}/{_model_prefix(uniprot_accession)}-model_v4.pdb"


def get_mmcif_url(uniprot_accession: str) -> str:
    return f"{FILES_BASE}/{_model_prefix(uniprot_accession)}-model_v4.cif"


def get_pae_url(uniprot_accession: str) -> str:
    return f"{FILES_BASE}/{_model_prefix(uniprot_accession)}-predicted_aligned_error_v4.json"


def get_structure_urls(uniprot_accession: str) -> Dict[str, str]:
    accession = (uniprot_accession or "").strip()
    if not accession:
        return {"pdb_url": "", "mmcif_url": "", "pae_url": ""}
    return {
        "pdb_url": get_pdb_url(accession),
        "mmcif_url": get_mmcif_url(accession),
        "pae_url": get_pae_url(accession),
    }


def get_alphafold_structure_urls(uniprot_accession: str) -> Dict[str, str]:
    return get_structure_urls(uniprot_accession)


def get_alphafold_metadata(uniprot_accession: str) -> Dict[str, Any]:
    accession = (uniprot_accession or "").strip()
    if not accession:
        return {"source": SOURCE_NAME, "available": False, "entries": [], "error": "Missing UniProt accession"}
    cache_key = f"alphafold:metadata:{accession}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached
    response = requests.get(f"{API_BASE}/{accession}", timeout=TIMEOUT_SECONDS, headers={"Accept": "application/json"})
    response.raise_for_status()
    entries = response.json()
    result = {
        "source": SOURCE_NAME,
        "available": bool(entries),
        "entries": entries if isinstance(entries, list) else [],
        "error": None,
    }
    set_cached(cache_key, result)
    return result


def get_alphafold_prediction(uniprot_accession: str) -> Dict[str, Any]:
    return get_alphafold_metadata(uniprot_accession)


def _confidence_label(score: Optional[float]) -> str:
    if score is None:
        return "unknown"
    if score >= 90:
        return "very high"
    if score >= 70:
        return "confident"
    if score >= 50:
        return "low"
    return "very low"


def _fetch_pdb_text(uniprot_accession: str) -> str:
    accession = (uniprot_accession or "").strip()
    if not accession:
        return ""
    cache_key = f"alphafold:pdb:{accession}"
    cached = get_cached(cache_key)
    if isinstance(cached, str):
        return cached
    response = requests.get(
        get_pdb_url(accession),
        timeout=TIMEOUT_SECONDS,
        headers={"Accept": "chemical/x-pdb,text/plain,*/*"},
    )
    response.raise_for_status()
    text = response.text
    set_cached(cache_key, text)
    return text


def _residue_plddt_from_pdb(pdb_text: str, position: Optional[int]) -> Optional[float]:
    if not pdb_text or not position:
        return None
    scores: list[float] = []
    for line in pdb_text.splitlines():
        if not line.startswith(("ATOM  ", "HETATM")):
            continue
        try:
            residue_number = int(line[22:26].strip())
            if residue_number != position:
                continue
            scores.append(float(line[60:66].strip()))
        except ValueError:
            continue
    if not scores:
        return None
    return round(sum(scores) / len(scores), 2)


def _global_plddt_from_pdb(pdb_text: str) -> Optional[float]:
    if not pdb_text:
        return None
    scores: list[float] = []
    for index, line in enumerate(pdb_text.splitlines()):
        if index > 10000:
            break
        if not line.startswith(("ATOM  ", "HETATM")):
            continue
        try:
            scores.append(float(line[60:66].strip()))
        except ValueError:
            continue
    if not scores:
        return None
    return round(sum(scores) / len(scores), 2)


def fetch_residue_confidence(uniprot_accession: str, position: Optional[int]) -> Dict[str, Any]:
    metadata = safe_get_alphafold_metadata(uniprot_accession)
    if not metadata.get("available"):
        return {
            "position": position,
            "residue_confidence": None,
            "global_confidence": None,
            "confidence_label": "unknown",
            "notes": "AlphaFold structure unavailable, so residue confidence cannot be checked.",
        }
    entry = (metadata.get("entries") or [{}])[0]
    global_score = entry.get("confidenceScore") or entry.get("plddt")
    score = float(global_score) if isinstance(global_score, (int, float)) else None
    residue_score: Optional[float] = None
    try:
        pdb_text = _fetch_pdb_text(uniprot_accession)
        residue_score = _residue_plddt_from_pdb(pdb_text, position)
        if score is None:
            score = _global_plddt_from_pdb(pdb_text)
    except Exception:
        residue_score = None
    effective_score = residue_score if residue_score is not None else score
    label = _confidence_label(effective_score)
    return {
        "position": position,
        "residue_confidence": residue_score,
        "global_confidence": score,
        "confidence_label": label,
        "notes": (
            f"Position {position} is mapped onto the available AlphaFold model. "
            "Residue pLDDT is read from the AlphaFold PDB confidence column when present."
            if position
            else "No protein residue position was available for AlphaFold mapping."
        ),
    }


def get_residue_confidence(uniprot_accession: str, position: Optional[int]) -> Dict[str, Any]:
    return fetch_residue_confidence(uniprot_accession, position)


def get_structure_status(uniprot_accession: str, position: Optional[int] = None) -> Dict[str, Any]:
    accession = (uniprot_accession or "").strip()
    urls = get_structure_urls(accession)
    metadata = safe_get_alphafold_metadata(accession)
    residue = fetch_residue_confidence(accession, position) if accession else {
        "position": position,
        "residue_confidence": None,
        "global_confidence": None,
        "confidence_label": "unknown",
        "notes": "Missing UniProt accession.",
    }
    return {
        "source": SOURCE_NAME,
        "uniprot_accession": accession or "unknown",
        "alphafold_available": bool(metadata.get("available")),
        **urls,
        **residue,
        "error": metadata.get("error"),
    }


def build_alphafold_summary(uniprot_accession: str, position: Optional[int] = None) -> Dict[str, Any]:
    status = safe_get_structure_status(uniprot_accession, position=position)
    accession = status.get("uniprot_accession") or (uniprot_accession or "unknown")
    available = bool(status.get("alphafold_available"))
    confidence = status.get("residue_confidence")
    global_confidence = status.get("global_confidence")
    confidence_label = status.get("confidence_label") or "unknown"
    if available:
        position_text = f" at residue {position}" if position else ""
        summary = (
            f"AlphaFold DB has a predicted structure for {accession}{position_text}. "
            f"The model confidence is {confidence_label}"
            + (
                f" with residue pLDDT {confidence:.1f}."
                if isinstance(confidence, (int, float))
                else f" with global pLDDT {global_confidence:.1f}."
                if isinstance(global_confidence, (int, float))
                else "."
            )
        )
        message = "Structure links are available from AlphaFold DB."
    else:
        summary = f"AlphaFold DB did not return a predicted structure for {accession}."
        message = status.get("error") or "No AlphaFold prediction was found for this accession."
    return {
        "source": SOURCE_NAME,
        "uniprot_accession": accession,
        "alphafold_available": available,
        "pdb_url": status.get("pdb_url") or "",
        "cif_url": status.get("mmcif_url") or status.get("cif_url") or "",
        "mmcif_url": status.get("mmcif_url") or status.get("cif_url") or "",
        "pae_url": status.get("pae_url") or "",
        "mutation_position": position,
        "residue_confidence": confidence,
        "global_confidence": global_confidence,
        "confidence_label": confidence_label,
        "summary": summary,
        "message": message,
        "error": status.get("error"),
    }


def safe_get_alphafold_metadata(uniprot_accession: str) -> Dict[str, Any]:
    try:
        return get_alphafold_metadata(uniprot_accession)
    except Exception as exc:  # noqa: BLE001
        return {"source": SOURCE_NAME, "available": False, "entries": [], "error": str(exc)}


def safe_get_structure_status(uniprot_accession: str, position: Optional[int] = None) -> Dict[str, Any]:
    try:
        return get_structure_status(uniprot_accession, position=position)
    except Exception as exc:  # noqa: BLE001
        return {
            "source": SOURCE_NAME,
            "uniprot_accession": uniprot_accession or "unknown",
            "alphafold_available": False,
            "pdb_url": "",
            "mmcif_url": "",
            "pae_url": "",
            "position": position,
            "residue_confidence": None,
            "global_confidence": None,
            "confidence_label": "unknown",
            "notes": "AlphaFold structure unavailable.",
            "error": str(exc),
        }
