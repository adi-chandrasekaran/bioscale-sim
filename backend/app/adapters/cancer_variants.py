from __future__ import annotations

from typing import Any, Dict

import requests

from app.adapters.cache import get_cached, set_cached
from app.adapters.normalizer import normalize_gene_symbol

SOURCE_NAME = "CIViC"
BASE_URL = "https://civicdb.org/api"
TIMEOUT_SECONDS = 20


def fetch_cancer_variant_context(gene_symbol: str, mutation_notation: str) -> Dict[str, Any]:
    symbol = normalize_gene_symbol(gene_symbol)
    notation = (mutation_notation or "").strip()
    cache_key = f"civic:variant:{symbol}:{notation}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached
    if not symbol or not notation:
        return {"source": SOURCE_NAME, "available": False, "error": "Missing gene or mutation"}

    response = requests.get(
        f"{BASE_URL}/variants",
        params={"q": f"{symbol} {notation}", "count": 5},
        timeout=TIMEOUT_SECONDS,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    records = payload.get("records") or payload.get("result") or []
    hits = []
    for row in records[:5]:
        name = row.get("name") or row.get("variant_name") or ""
        gene = row.get("gene") or {}
        gene_name = gene.get("name") if isinstance(gene, dict) else ""
        if symbol not in f"{gene_name} {name}".upper():
            continue
        hits.append(
            {
                "id": row.get("id"),
                "name": name,
                "gene": gene_name or symbol,
                "description": row.get("description") or row.get("summary"),
                "source": SOURCE_NAME,
            }
        )
    result = {
        "source": SOURCE_NAME,
        "available": bool(hits),
        "gene_symbol": symbol,
        "mutation_notation": notation,
        "records": hits,
        "error": None,
    }
    set_cached(cache_key, result)
    return result


def safe_fetch_cancer_variant_context(gene_symbol: str, mutation_notation: str) -> Dict[str, Any]:
    try:
        return fetch_cancer_variant_context(gene_symbol, mutation_notation)
    except Exception as exc:  # noqa: BLE001
        return {
            "source": SOURCE_NAME,
            "available": False,
            "gene_symbol": normalize_gene_symbol(gene_symbol),
            "mutation_notation": mutation_notation,
            "records": [],
            "error": str(exc),
        }
