from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from app.adapters.cache import get_cached, set_cached

SOURCE_NAME = "AlphaFold DB"
API_BASE = "https://alphafold.ebi.ac.uk/api/prediction"
FILES_BASE = "https://alphafold.ebi.ac.uk/files"
RCSB_FILES_BASE = "https://files.rcsb.org/download"
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
        return "unavailable"
    if score >= 90:
        return "very high"
    if score >= 70:
        return "confident"
    if score >= 50:
        return "low"
    return "very low"


def fetch_pdb_text(uniprot_accession: str) -> str:
    accession = (uniprot_accession or "").strip()
    if not accession:
        return ""
    cache_key = f"alphafold:pdb:{accession}"
    cached = get_cached(cache_key)
    if isinstance(cached, str):
        return cached
    metadata = safe_get_alphafold_metadata(accession)
    entry = (metadata.get("entries") or [{}])[0]
    candidate_urls = [
        entry.get("pdbUrl") or entry.get("pdb_url"),
        get_pdb_url(accession),
        f"{FILES_BASE}/{_model_prefix(accession)}-model_v6.pdb",
        f"{FILES_BASE}/{_model_prefix(accession)}-model_v5.pdb",
        f"{FILES_BASE}/{_model_prefix(accession)}-model_v3.pdb",
    ]
    last_error: Exception | None = None
    for url in dict.fromkeys(item for item in candidate_urls if item):
        try:
            response = requests.get(
                url,
                timeout=TIMEOUT_SECONDS,
                headers={"Accept": "chemical/x-pdb,text/plain,*/*"},
            )
            response.raise_for_status()
            text = response.text
            if text.strip():
                set_cached(cache_key, text)
                return text
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    if last_error:
        raise last_error
    return ""


def _metadata_entry_urls(entry: dict[str, Any], accession: str) -> Dict[str, str]:
    return {
        "pdb_url": entry.get("pdbUrl") or entry.get("pdb_url") or get_pdb_url(accession),
        "mmcif_url": entry.get("cifUrl") or entry.get("cif_url") or entry.get("mmcif_url") or get_mmcif_url(accession),
        "pae_url": entry.get("paeDocUrl") or entry.get("pae_url") or entry.get("paeDocURL") or get_pae_url(accession),
    }


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
    pdb_text = ""
    pdb_error = ""
    try:
        pdb_text = fetch_pdb_text(uniprot_accession)
    except Exception as exc:  # noqa: BLE001
        pdb_error = str(exc)
    if not metadata.get("available") and not pdb_text:
        return {
            "position": position,
            "residue_confidence": None,
            "global_confidence": None,
            "confidence_label": "unavailable",
            "notes": "AlphaFold structure unavailable, so residue confidence cannot be checked.",
            "error_message": pdb_error or metadata.get("error") or "No AlphaFold structure metadata or PDB text was available.",
        }
    entry = (metadata.get("entries") or [{}])[0]
    global_score = entry.get("confidenceScore") or entry.get("plddt")
    score = float(global_score) if isinstance(global_score, (int, float)) else None
    residue_score: Optional[float] = None
    if pdb_text:
        residue_score = _residue_plddt_from_pdb(pdb_text, position)
        if score is None:
            score = _global_plddt_from_pdb(pdb_text)
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
        "error_message": None if effective_score is not None else (pdb_error or "Could not parse residue/global pLDDT from AlphaFold metadata or PDB B-factor column."),
    }


def get_residue_confidence(uniprot_accession: str, position: Optional[int]) -> Dict[str, Any]:
    return fetch_residue_confidence(uniprot_accession, position)


def get_structure_status(uniprot_accession: str, position: Optional[int] = None) -> Dict[str, Any]:
    accession = (uniprot_accession or "").strip()
    urls = get_structure_urls(accession)
    metadata = safe_get_alphafold_metadata(accession)
    entry = (metadata.get("entries") or [{}])[0]
    if accession:
        urls.update(_metadata_entry_urls(entry, accession))
    pdb_available = False
    pdb_error = ""
    if accession:
        try:
            pdb_available = bool(fetch_pdb_text(accession))
        except Exception as exc:  # noqa: BLE001
            pdb_error = str(exc)
    residue = fetch_residue_confidence(accession, position) if accession else {
        "position": position,
        "residue_confidence": None,
        "global_confidence": None,
        "confidence_label": "unavailable",
        "notes": "Missing UniProt accession.",
    }
    structure_source = "alphafold" if bool(metadata.get("available") or pdb_available) else (
        "rcsb_pdb" if _uniprot_pdb_crossrefs(accession) else (
            "uniprot_feature_map" if _uniprot_feature_model(accession, position).get("features") else "none_found"
        )
    )
    structure_source_label = "AlphaFold DB" if structure_source == "alphafold" else (
        "RCSB PDB" if structure_source == "rcsb_pdb" else (
            "UniProt feature map" if structure_source == "uniprot_feature_map" else "No public structure record found after checks"
        )
    )
    return {
        "source": SOURCE_NAME,
        "uniprot_accession": accession or "unknown",
        "alphafold_available": bool(metadata.get("available") or pdb_available),
        "structure_source": structure_source,
        "structure_source_label": structure_source_label,
        "structure_status_reason": (
            "AlphaFold DB returned a predicted structure for the resolved UniProt accession."
            if structure_source == "alphafold"
            else "AlphaFold DB had no public model, so a secondary structure/context source was selected."
            if structure_source in {"rcsb_pdb", "uniprot_feature_map"}
            else "No public structure record was found after AlphaFold, PDB, and UniProt feature checks."
        ),
        "structure_view_model": _uniprot_feature_model(accession, position),
        **urls,
        **residue,
        "error": metadata.get("error") if not pdb_available else None,
        "pdb_fetch_error": pdb_error,
    }


def _parse_mutation_residues(mutation: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    text = (mutation or "").strip()
    if not text.startswith("p."):
        return None, None
    code = text[2:]
    amino3 = {
        "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C",
        "Gln": "Q", "Glu": "E", "Gly": "G", "His": "H", "Ile": "I",
        "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F", "Pro": "P",
        "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V",
    }
    for three, one in amino3.items():
        code = code.replace(three, one)
    letters = [char for char in code if char.isalpha() or char == "*"]
    if len(letters) >= 2:
        return letters[0], letters[-1]
    return (letters[0], None) if letters else (None, None)


def _safe_uniprot_domain_hit(uniprot_accession: str, position: Optional[int]) -> Optional[str]:
    if not uniprot_accession or not position:
        return None
    cache_key = f"uniprot:features:{uniprot_accession}"
    cached = get_cached(cache_key)
    if cached is None:
        response = requests.get(f"https://rest.uniprot.org/uniprotkb/{uniprot_accession}.json", timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        cached = response.json()
        set_cached(cache_key, cached)
    for feature in cached.get("features", []):
        start = feature.get("location", {}).get("start", {}).get("value")
        end = feature.get("location", {}).get("end", {}).get("value")
        if isinstance(start, int) and isinstance(end, int) and start <= position <= end:
            kind = feature.get("type") or "feature"
            description = feature.get("description") or "unnamed region"
            return f"{kind}: {description} ({start}-{end})"
    return None


def _safe_uniprot_entry(uniprot_accession: str) -> Dict[str, Any]:
    accession = (uniprot_accession or "").strip()
    if not accession:
        return {}
    cache_key = f"uniprot:structure-context:{accession}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached
    response = requests.get(f"https://rest.uniprot.org/uniprotkb/{accession}.json", timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    set_cached(cache_key, payload)
    return payload


def _uniprot_pdb_crossrefs(uniprot_accession: str) -> list[Dict[str, Any]]:
    try:
        entry = _safe_uniprot_entry(uniprot_accession)
    except Exception:
        return []
    refs = []
    for ref in entry.get("uniProtKBCrossReferences", []):
        if ref.get("database") != "PDB" or not ref.get("id"):
            continue
        properties = {item.get("key"): item.get("value") for item in ref.get("properties", []) if item.get("key")}
        refs.append(
            {
                "id": ref.get("id"),
                "method": properties.get("Method"),
                "resolution": properties.get("Resolution"),
                "chains": properties.get("Chains"),
                "source": "RCSB PDB",
            }
        )
    return refs


def _uniprot_feature_model(uniprot_accession: str, position: Optional[int]) -> Dict[str, Any]:
    try:
        entry = _safe_uniprot_entry(uniprot_accession)
    except Exception as exc:  # noqa: BLE001
        return {"features": [], "sequence_length": None, "position": position, "error": str(exc)}
    sequence_length = entry.get("sequence", {}).get("length")
    features = []
    for feature in entry.get("features", []):
        start = feature.get("location", {}).get("start", {}).get("value")
        end = feature.get("location", {}).get("end", {}).get("value")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        feature_type = feature.get("type") or "feature"
        if feature_type not in {"Domain", "Region", "DNA binding", "Zinc finger", "Motif", "Site", "Binding site", "Active site"}:
            continue
        features.append(
            {
                "type": feature_type,
                "description": feature.get("description") or feature_type,
                "start": start,
                "end": end,
                "contains_position": bool(position and start <= position <= end),
            }
        )
    return {
        "features": features[:30],
        "sequence_length": sequence_length,
        "position": position,
        "source": "UniProt feature map",
        "error": None,
    }


def build_alphafold_summary(uniprot_accession: str, position: Optional[int] = None, mutation: Optional[str] = None) -> Dict[str, Any]:
    status = safe_get_structure_status(uniprot_accession, position=position)
    accession = status.get("uniprot_accession") or (uniprot_accession or "unknown")
    available = bool(status.get("alphafold_available"))
    confidence = status.get("residue_confidence")
    global_confidence = status.get("global_confidence")
    confidence_label = status.get("confidence_label") or "unavailable"
    normal_residue, mutant_residue = _parse_mutation_residues(mutation)
    domain_hit = None
    try:
        domain_hit = _safe_uniprot_domain_hit(accession, position)
    except Exception:
        domain_hit = None
    if available:
        structure_source = "alphafold"
        structure_source_label = "AlphaFold DB"
        structure_status_reason = "AlphaFold DB returned a predicted structure for the resolved UniProt accession."
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
        pdb_refs = _uniprot_pdb_crossrefs(accession)
        feature_model = _uniprot_feature_model(accession, position)
        if pdb_refs:
            structure_source = "rcsb_pdb"
            structure_source_label = "RCSB PDB"
            structure_status_reason = "AlphaFold DB had no public model, so UniProt PDB cross-references were used."
            primary_pdb = pdb_refs[0]["id"]
            status["pdb_url"] = f"{RCSB_FILES_BASE}/{primary_pdb}.pdb"
            status["mmcif_url"] = f"{RCSB_FILES_BASE}/{primary_pdb}.cif"
            summary = (
                f"AlphaFold DB did not return a predicted structure for {accession}. "
                f"RCSB PDB has an experimental structure mapping via UniProt cross-reference {primary_pdb}."
            )
            message = f"Using RCSB PDB structure {primary_pdb} as the structural source."
        elif feature_model.get("features"):
            structure_source = "uniprot_feature_map"
            structure_source_label = "UniProt feature map"
            structure_status_reason = "No public 3D model was found, so UniProt sequence features and domains were used."
            summary = (
                f"No AlphaFold or PDB structure was found for {accession}. "
                "UniProt protein features are shown as the structural context."
            )
            message = "Using UniProt feature/domain map because no public 3D structure record was found."
        else:
            structure_source = "none_found"
            structure_source_label = "No public structure record found after checks"
            structure_status_reason = "AlphaFold DB, UniProt PDB cross-references, and UniProt feature records did not provide structural context."
            summary = f"No public structure or feature record was found for {accession} after AlphaFold, PDB, and UniProt feature checks."
            message = status.get("error") or "No public structure record was found for this accession."
        if "pdb_refs" not in locals():
            pdb_refs = []
        if "feature_model" not in locals():
            feature_model = _uniprot_feature_model(accession, position)
    return {
        "source": SOURCE_NAME,
        "uniprot_accession": accession,
        "alphafold_available": available,
        "structure_source": structure_source,
        "structure_source_label": structure_source_label,
        "structure_status_reason": structure_status_reason,
        "structure_view_model": feature_model if "feature_model" in locals() else _uniprot_feature_model(accession, position),
        "pdb_crossrefs": pdb_refs if "pdb_refs" in locals() else [],
        "pdb_url": status.get("pdb_url") or "",
        "cif_url": status.get("mmcif_url") or status.get("cif_url") or "",
        "mmcif_url": status.get("mmcif_url") or status.get("cif_url") or "",
        "pae_url": status.get("pae_url") or "",
        "mutation_position": position,
        "normal_residue": normal_residue,
        "mutant_residue": mutant_residue,
        "domain_hit": domain_hit,
        "residue_confidence": confidence,
        "global_confidence": global_confidence,
        "confidence_label": confidence_label,
        "summary": summary,
        "message": message,
        "error": status.get("error"),
        "error_message": status.get("error_message") or status.get("pdb_fetch_error") or status.get("error"),
        "pdb_proxy_url": f"/api/structure/alphafold/pdb?uniprot_accession={accession}",
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
            "confidence_label": "unavailable",
            "notes": "AlphaFold structure unavailable.",
            "error": str(exc),
            "error_message": str(exc),
        }
