from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from app.adapters.cache import get_cached, set_cached
from app.adapters.normalizer import get_uniprot_accession, normalize_gene_symbol, normalize_reactome_pathway

BASE_URL = "https://reactome.org/ContentService"
TIMEOUT_SECONDS = 25
SOURCE_NAME = "Reactome"

# Future adapter stubs (not wired in Phase 1).
FUTURE_ADAPTERS = {
    "STRING": "Protein-protein interaction network enrichment (TODO)",
    "gnomAD": "Population allele frequency context (TODO)",
    "AlphaFold": "Structural confidence and mutation proximity (TODO)",
    "Human Protein Atlas": "Tissue expression atlas (TODO)",
    "TCGA": "Tumor alteration prevalence (TODO)",
}


def _fetch_json(url: str) -> Any:
    response = requests.get(url, timeout=TIMEOUT_SECONDS, headers={"Accept": "application/json"})
    response.raise_for_status()
    return response.json()


def search_pathways(query: str, limit: int = 10) -> Dict[str, Any]:
    cache_key = f"reactome:search_pathways:{query.lower()}:{limit}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    response = requests.get(
        f"{BASE_URL}/search/query",
        params={"query": query, "species": "Homo sapiens", "types": "Pathway", "cluster": "true"},
        timeout=TIMEOUT_SECONDS,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    results = []
    for group in (payload.get("results") or [])[:limit]:
        entries = group.get("entries") or []
        if not entries:
            continue
        entry = entries[0]
        results.append(
            {
                "stId": entry.get("stId"),
                "displayName": entry.get("name"),
                "species": entry.get("species"),
                "source": SOURCE_NAME,
            }
        )
    result = {"source": SOURCE_NAME, "available": bool(results), "query": query, "results": results, "error": None}
    set_cached(cache_key, result)
    return result


def search_pathways_for_gene(gene_symbol: str, query: str = "", limit: int = 10) -> Dict[str, Any]:
    evidence = fetch_pathway_evidence(gene_symbol)
    pathways = evidence.get("pathways", [])
    if query.strip():
        q = query.lower()
        pathways = [p for p in pathways if q in (p.get("displayName") or "").lower()]
    pathways = pathways[:limit]
    return {
        "source": SOURCE_NAME,
        "available": bool(pathways),
        "query": query or gene_symbol,
        "gene_symbol": normalize_gene_symbol(gene_symbol),
        "results": pathways,
        "error": evidence.get("error"),
    }


def safe_search_pathways(query: str, gene: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    if not query.strip() and not gene:
        return {"source": SOURCE_NAME, "available": False, "query": query, "results": [], "error": "Empty query"}
    try:
        if gene:
            return search_pathways_for_gene(gene, query=query, limit=limit)
        return search_pathways(query, limit=limit)
    except Exception as exc:  # noqa: BLE001
        return {"source": SOURCE_NAME, "available": False, "query": query, "results": [], "error": str(exc)}


def fetch_pathway_evidence(
    gene_symbol: str,
    local_kb: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return Reactome pathways and participants for a gene's UniProt accession."""
    symbol = normalize_gene_symbol(gene_symbol)
    accession = get_uniprot_accession(symbol, local_kb)
    cache_key = f"reactome:pathways:{accession}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    if not accession:
        return {
            "source": SOURCE_NAME,
            "available": False,
            "gene_symbol": symbol,
            "accession": None,
            "pathways": [],
            "participants": [],
            "error": f"No UniProt accession for {symbol}",
        }

    pathways_raw = _fetch_json(f"{BASE_URL}/data/pathways/low/entity/{accession}")
    participants_raw: List[Dict[str, Any]] = []
    try:
        participants_raw = _fetch_json(f"{BASE_URL}/data/participants/{accession}")
    except Exception:
        participants_raw = []

    pathways = [normalize_reactome_pathway(p) for p in (pathways_raw or []) if isinstance(p, dict)]
    participants = []
    for item in participants_raw or []:
        if not isinstance(item, dict):
            continue
        participants.append(
            {
                "displayName": item.get("displayName"),
                "stId": item.get("stId"),
                "schemaClass": item.get("schemaClass"),
            }
        )

    result = {
        "source": SOURCE_NAME,
        "available": bool(pathways),
        "gene_symbol": symbol,
        "accession": accession,
        "pathways": pathways[:15],
        "participants": participants[:25],
        "future_adapters": FUTURE_ADAPTERS,
        "error": None,
    }
    set_cached(cache_key, result)
    return result


def safe_fetch_pathway_evidence(
    gene_symbol: str,
    local_kb: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        return fetch_pathway_evidence(gene_symbol, local_kb)
    except Exception as exc:  # noqa: BLE001
        symbol = normalize_gene_symbol(gene_symbol)
        return {
            "source": SOURCE_NAME,
            "available": False,
            "gene_symbol": symbol,
            "accession": get_uniprot_accession(symbol, local_kb),
            "pathways": [],
            "participants": [],
            "future_adapters": FUTURE_ADAPTERS,
            "error": str(exc),
        }
