from __future__ import annotations

from typing import Any, Dict

import requests

from app.adapters.cache import get_cached, set_cached
from app.adapters.normalizer import normalize_gene_symbol

BASE_URL = "https://rest.genenames.org"
TIMEOUT_SECONDS = 20
SOURCE_NAME = "HGNC"


def fetch_gene_identity(gene_symbol: str) -> Dict[str, Any]:
    symbol = normalize_gene_symbol(gene_symbol)
    if not symbol:
        return {"source": SOURCE_NAME, "available": False, "query": gene_symbol, "error": "Empty gene symbol"}
    cache_key = f"hgnc:gene:{symbol}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    response = requests.get(
        f"{BASE_URL}/fetch/symbol/{symbol}",
        timeout=TIMEOUT_SECONDS,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    docs = response.json().get("response", {}).get("docs", [])
    if not docs:
        alias_response = requests.get(
            f"{BASE_URL}/search/{symbol}",
            timeout=TIMEOUT_SECONDS,
            headers={"Accept": "application/json"},
        )
        alias_response.raise_for_status()
        docs = alias_response.json().get("response", {}).get("docs", [])
    doc = docs[0] if docs else {}
    result = {
        "source": SOURCE_NAME,
        "available": bool(doc),
        "query": symbol,
        "symbol": doc.get("symbol") or symbol,
        "name": doc.get("name"),
        "hgnc_id": doc.get("hgnc_id"),
        "ensembl_id": doc.get("ensembl_gene_id"),
        "uniprot_ids": doc.get("uniprot_ids") or [],
        "alias_symbols": doc.get("alias_symbol") or [],
        "summary": doc.get("name"),
        "error": None,
    }
    set_cached(cache_key, result)
    return result


def safe_fetch_gene_identity(gene_symbol: str) -> Dict[str, Any]:
    try:
        return fetch_gene_identity(gene_symbol)
    except Exception as exc:  # noqa: BLE001
        symbol = normalize_gene_symbol(gene_symbol)
        return {
            "source": SOURCE_NAME,
            "available": False,
            "query": symbol,
            "symbol": symbol,
            "uniprot_ids": [],
            "error": str(exc),
        }
