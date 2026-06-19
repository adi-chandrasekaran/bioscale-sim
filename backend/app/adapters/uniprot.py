from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from app.adapters.cache import get_cached, set_cached
from app.adapters.normalizer import get_uniprot_accession, normalize_gene_symbol

BASE_URL = "https://rest.uniprot.org/uniprotkb"
TIMEOUT_SECONDS = 25
SOURCE_NAME = "UniProt"


def _fetch_json(url: str) -> Dict[str, Any]:
    response = requests.get(url, timeout=TIMEOUT_SECONDS, headers={"Accept": "application/json"})
    response.raise_for_status()
    return response.json()


def _extract_protein_name(entry: Dict[str, Any]) -> str:
    protein = entry.get("proteinDescription", {})
    rec = protein.get("recommendedName", {})
    full = rec.get("fullName", {}).get("value")
    if full:
        return full
    submission = protein.get("submissionNames", [])
    if submission:
        return submission[0].get("fullName", {}).get("value", "unknown")
    return entry.get("uniProtkbId", "unknown")


def _extract_function(entry: Dict[str, Any]) -> str:
    comments = entry.get("comments", [])
    functions: List[str] = []
    for comment in comments:
        if comment.get("commentType") == "FUNCTION":
            texts = comment.get("texts", [])
            for text in texts:
                value = text.get("value")
                if value:
                    functions.append(value)
    return " ".join(functions[:2]) if functions else ""


def _extract_domains(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    domains: List[Dict[str, Any]] = []
    for feature in entry.get("features", []):
        ftype = feature.get("type", "")
        if ftype not in {"Domain", "Region", "DNA binding", "Zinc finger"}:
            continue
        location = feature.get("location", {})
        start = location.get("start", {}).get("value")
        end = location.get("end", {}).get("value")
        if start is None or end is None:
            continue
        domains.append(
            {
                "name": feature.get("description") or ftype,
                "start": int(start),
                "end": int(end),
            }
        )
    return domains


def _domain_at_position(domains: List[Dict[str, Any]], position: Optional[int]) -> Optional[str]:
    if position is None:
        return None
    for domain in domains:
        if domain["start"] <= position <= domain["end"]:
            return domain["name"]
    return None


def search_genes_uniprot(query: str, limit: int = 10) -> Dict[str, Any]:
    cache_key = f"uniprot:search_genes:{query.upper()}:{limit}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    params = {
        "query": f"(gene:{query}) AND (organism_id:9606)",
        "fields": "accession,gene_names,protein_name,organism_name,length",
        "size": limit,
    }
    response = requests.get(
        f"{BASE_URL}/search",
        params=params,
        timeout=TIMEOUT_SECONDS,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    results = []
    for row in payload.get("results", []):
        genes = row.get("genes", [])
        symbol = genes[0].get("geneName", {}).get("value") if genes else query.upper()
        results.append(
            {
                "accession": row.get("primaryAccession"),
                "symbol": (symbol or query).upper(),
                "protein_name": row.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value"),
                "organism": row.get("organism", {}).get("scientificName"),
                "sequence_length": row.get("sequence", {}).get("length"),
                "source": SOURCE_NAME,
            }
        )
    result = {"source": SOURCE_NAME, "available": bool(results), "query": query, "results": results, "error": None}
    set_cached(cache_key, result)
    return result


def safe_search_genes_uniprot(query: str, limit: int = 10) -> Dict[str, Any]:
    if not query.strip():
        return {"source": SOURCE_NAME, "available": False, "query": query, "results": [], "error": "Empty query"}
    try:
        return search_genes_uniprot(query, limit=limit)
    except Exception as exc:  # noqa: BLE001
        symbol = normalize_gene_symbol(query)
        accession = get_uniprot_accession(symbol)
        fallback = []
        if accession:
            fallback.append({"accession": accession, "symbol": symbol, "source": "Local fallback map"})
        return {"source": SOURCE_NAME, "available": bool(fallback), "query": query, "results": fallback, "error": str(exc)}


def fetch_protein_evidence(
    gene_symbol: str,
    local_kb: Optional[Dict[str, Any]] = None,
    mutation_position: Optional[int] = None,
) -> Dict[str, Any]:
    """Return normalized UniProt protein evidence."""
    symbol = normalize_gene_symbol(gene_symbol)
    accession = get_uniprot_accession(symbol, local_kb)
    cache_key = f"uniprot:protein:{accession}:{mutation_position}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    if not accession:
        return {
            "source": SOURCE_NAME,
            "available": False,
            "gene_symbol": symbol,
            "accession": None,
            "error": f"No UniProt accession mapping for {symbol}",
        }

    entry = _fetch_json(f"{BASE_URL}/{accession}.json")
    domains = _extract_domains(entry)
    gene_names = entry.get("genes", [])
    gene_name = gene_names[0].get("geneName", {}).get("value") if gene_names else symbol

    result = {
        "source": SOURCE_NAME,
        "available": True,
        "gene_symbol": symbol,
        "gene_name": gene_name,
        "accession": accession,
        "protein_name": _extract_protein_name(entry),
        "function_summary": _extract_function(entry),
        "function_raw": _extract_function(entry),
        "domains": domains,
        "mutation_position": mutation_position,
        "domain_hit": _domain_at_position(domains, mutation_position),
        "organism": entry.get("organism", {}).get("scientificName"),
        "sequence_length": entry.get("sequence", {}).get("length"),
        "raw_entry": entry,
        "error": None,
    }
    set_cached(cache_key, result)
    return result


def safe_fetch_protein_evidence(
    gene_symbol: str,
    local_kb: Optional[Dict[str, Any]] = None,
    mutation_position: Optional[int] = None,
) -> Dict[str, Any]:
    try:
        return fetch_protein_evidence(gene_symbol, local_kb, mutation_position)
    except Exception as exc:  # noqa: BLE001
        symbol = normalize_gene_symbol(gene_symbol)
        accession = get_uniprot_accession(symbol, local_kb)
        return {
            "source": SOURCE_NAME,
            "available": False,
            "gene_symbol": symbol,
            "accession": accession,
            "protein_name": None,
            "function_summary": None,
            "domains": [],
            "mutation_position": mutation_position,
            "domain_hit": None,
            "error": str(exc),
        }
