from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from app.adapters.cache import get_cached, set_cached
from app.adapters.normalizer import (
    hgvs_to_clinvar_query,
    normalize_clinvar_classification,
    normalize_gene_symbol,
    normalize_variant_query,
    parse_hgvs_protein,
)

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TIMEOUT_SECONDS = 25
SOURCE_NAME = "ClinVar"


def _eutils_get(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.get(
        f"{EUTILS_BASE}/{endpoint}",
        params={**params, "retmode": "json"},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def _search_clinvar_ids(gene_symbol: str, mutation_notation: str, retmax: int = 5) -> List[str]:
    term = hgvs_to_clinvar_query(gene_symbol, mutation_notation)
    payload = _eutils_get(
        "esearch.fcgi",
        {"db": "clinvar", "term": term, "retmax": retmax},
    )
    return payload.get("esearchresult", {}).get("idlist", [])


def _fetch_clinvar_summaries(variant_ids: List[str]) -> List[Dict[str, Any]]:
    if not variant_ids:
        return []
    payload = _eutils_get(
        "esummary.fcgi",
        {"db": "clinvar", "id": ",".join(variant_ids)},
    )
    result = payload.get("result", {})
    summaries: List[Dict[str, Any]] = []
    for uid in variant_ids:
        entry = result.get(uid)
        if not entry or uid == "uids":
            continue
        summaries.append(entry)
    return summaries


def _extract_classification(summary: Dict[str, Any]) -> str:
    germline = summary.get("germline_classification") or {}
    if isinstance(germline, dict):
        desc = germline.get("description") or germline.get("germline_classification_description")
        if desc:
            return normalize_clinvar_classification(str(desc))
    title = summary.get("title", "")
    for label in ("Pathogenic", "Likely pathogenic", "Benign", "Likely benign", "Uncertain significance"):
        if label.lower() in title.lower():
            return normalize_clinvar_classification(label)
    return "unknown"


def _extract_phenotypes(summary: Dict[str, Any]) -> List[str]:
    traits = summary.get("trait_set") or []
    phenotypes: List[str] = []
    for trait in traits:
        if isinstance(trait, dict):
            name = trait.get("trait_name")
            if name:
                phenotypes.append(name)
    return phenotypes[:5]


def search_variants(query: str, gene_symbol: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    norm = normalize_variant_query(query, gene_symbol)
    cache_key = f"clinvar:search:{norm['gene_symbol']}:{norm['query']}:{limit}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    if norm["is_rsid"]:
        term = norm["variant_text"]
        if norm["gene_symbol"]:
            term = f"{norm['gene_symbol']}[Gene] AND {norm['variant_text']}[Variant name]"
    elif norm["parsed"] and norm["gene_symbol"]:
        term = hgvs_to_clinvar_query(norm["gene_symbol"], norm["notation"])
    elif norm["gene_symbol"]:
        term = f"{norm['gene_symbol']}[Gene] AND {norm['variant_text']}[Variant name]"
    else:
        term = norm["query"]

    payload = _eutils_get("esearch.fcgi", {"db": "clinvar", "term": term, "retmax": limit})
    variant_ids = payload.get("esearchresult", {}).get("idlist", [])
    summaries = _fetch_clinvar_summaries(variant_ids)

    results = []
    for summary in summaries:
        title = summary.get("title", "")
        results.append(
            {
                "id": str(summary.get("uid", "")),
                "title": title,
                "notation": norm["notation"],
                "gene_symbol": norm["gene_symbol"],
                "classification": _extract_classification(summary),
                "variant_type": _guess_variant_type(title, norm["parsed"]),
                "source": SOURCE_NAME,
            }
        )

    if not results and norm["parsed"]:
        parsed = norm["parsed"]
        results.append(
            {
                "id": None,
                "title": f"{norm['gene_symbol'] or 'Gene'} {norm['notation']}",
                "notation": norm["notation"],
                "gene_symbol": norm["gene_symbol"],
                "classification": None,
                "variant_type": "missense" if parsed["from_aa"] != parsed["to_aa"] else "unknown",
                "source": "HGVS parser",
                "parser_only": True,
            }
        )

    result = {
        "source": SOURCE_NAME,
        "available": bool(results),
        "query": query,
        "gene_symbol": norm["gene_symbol"],
        "results": results,
        "error": None,
    }
    set_cached(cache_key, result)
    return result


def _guess_variant_type(title: str, parsed: Optional[Dict[str, Any]]) -> str:
    lower = title.lower()
    if "missense" in lower:
        return "missense"
    if "frameshift" in lower:
        return "frameshift"
    if "nonsense" in lower or "stop gained" in lower:
        return "nonsense"
    if parsed and parsed.get("from_aa") != parsed.get("to_aa"):
        return "missense"
    return "unknown"


def safe_search_variants(query: str, gene_symbol: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    if not query.strip():
        return {"source": SOURCE_NAME, "available": False, "query": query, "results": [], "error": "Empty query"}
    try:
        return search_variants(query, gene_symbol=gene_symbol, limit=limit)
    except Exception as exc:  # noqa: BLE001
        norm = normalize_variant_query(query, gene_symbol)
        fallback = []
        if norm["parsed"]:
            parsed = norm["parsed"]
            fallback.append(
                {
                    "id": None,
                    "title": f"{norm['gene_symbol'] or 'Gene'} {norm['notation']}",
                    "notation": norm["notation"],
                    "gene_symbol": norm["gene_symbol"],
                    "classification": None,
                    "variant_type": "missense",
                    "source": "HGVS parser",
                    "parser_only": True,
                }
            )
        return {
            "source": SOURCE_NAME,
            "available": bool(fallback),
            "query": query,
            "gene_symbol": norm["gene_symbol"],
            "results": fallback,
            "error": str(exc),
        }


def fetch_variant_evidence(gene_symbol: str, mutation_notation: str) -> Dict[str, Any]:
    """Return normalized ClinVar evidence for a gene + HGVS protein variant."""
    symbol = normalize_gene_symbol(gene_symbol)
    parsed = parse_hgvs_protein(mutation_notation)
    cache_key = f"clinvar:variant:{symbol}:{mutation_notation}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    variant_ids = _search_clinvar_ids(symbol, mutation_notation)
    summaries = _fetch_clinvar_summaries(variant_ids)

    classification = "unknown"
    phenotypes: List[str] = []
    variant_type = parsed and "missense" if parsed and parsed["from_aa"] != parsed["to_aa"] else "unknown"
    clinvar_ids: List[str] = []

    if summaries:
        primary = summaries[0]
        classification = _extract_classification(primary)
        phenotypes = _extract_phenotypes(primary)
        clinvar_ids = [str(s.get("uid", "")) for s in summaries if s.get("uid")]
        title = primary.get("title", "")
        if "missense" in title.lower():
            variant_type = "missense"
        elif "frameshift" in title.lower():
            variant_type = "frameshift"
        elif "nonsense" in title.lower() or "stop gained" in title.lower():
            variant_type = "nonsense"

    result = {
        "source": SOURCE_NAME,
        "available": bool(summaries),
        "gene_symbol": symbol,
        "mutation_notation": mutation_notation,
        "variant_type": variant_type,
        "amino_acid_change": (
            f"{parsed['from_aa']}→{parsed['to_aa']} at position {parsed['position']}"
            if parsed
            else None
        ),
        "clinvar_classification": classification,
        "phenotypes": phenotypes,
        "clinvar_ids": clinvar_ids,
        "records_found": len(summaries),
        "error": None,
    }
    set_cached(cache_key, result)
    return result


def safe_fetch_variant_evidence(gene_symbol: str, mutation_notation: str) -> Dict[str, Any]:
    try:
        return fetch_variant_evidence(gene_symbol, mutation_notation)
    except Exception as exc:  # noqa: BLE001
        parsed = parse_hgvs_protein(mutation_notation)
        return {
            "source": SOURCE_NAME,
            "available": False,
            "gene_symbol": normalize_gene_symbol(gene_symbol),
            "mutation_notation": mutation_notation,
            "variant_type": "unknown",
            "amino_acid_change": (
                f"{parsed['from_aa']}→{parsed['to_aa']} at position {parsed['position']}"
                if parsed
                else None
            ),
            "clinvar_classification": None,
            "phenotypes": [],
            "clinvar_ids": [],
            "records_found": 0,
            "error": str(exc),
        }
