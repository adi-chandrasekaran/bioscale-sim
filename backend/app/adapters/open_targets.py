from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from app.adapters.cache import get_cached, set_cached
from app.adapters.normalizer import get_ensembl_id, normalize_disease, normalize_gene_symbol

BASE_URL = "https://api.platform.opentargets.org/api/v4/graphql"
TIMEOUT_SECONDS = 25
SOURCE_NAME = "Open Targets"


def _graphql_query(query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    response = requests.post(
        BASE_URL,
        json={"query": query, "variables": variables or {}},
        timeout=TIMEOUT_SECONDS,
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0].get("message", "Open Targets GraphQL error"))
    return payload


def fetch_disease_targets_by_id(efo_id: str, limit: int = 10) -> Dict[str, Any]:
    """Return disease-target associations for an Open Targets disease ID."""
    cache_key = f"open_targets:disease_targets_id:{efo_id}:{limit}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    query = """
    query DiseaseTargets($efoId: String!, $size: Int!) {
      disease(efoId: $efoId) {
        id
        name
        description
        associatedTargets(page: { index: 0, size: $size }) {
          rows {
            score
            target {
              id
              approvedSymbol
              approvedName
            }
          }
        }
      }
    }
    """
    payload = _graphql_query(query, {"efoId": efo_id, "size": limit})
    disease = payload.get("data", {}).get("disease") or {}
    rows = disease.get("associatedTargets", {}).get("rows", [])

    candidates: List[Dict[str, Any]] = []
    for row in rows:
        target = row.get("target") or {}
        symbol = target.get("approvedSymbol")
        if not symbol:
            continue
        score = float(row.get("score") or 0.0)
        candidates.append(
            {
                "symbol": symbol,
                "score": round(score, 4),
                "ensembl_id": target.get("id"),
                "name": target.get("approvedName"),
                "source": SOURCE_NAME,
            }
        )

    result = {
        "source": SOURCE_NAME,
        "available": bool(candidates),
        "disease_id": disease.get("id") or efo_id,
        "disease_name": disease.get("name") or efo_id,
        "disease_description": disease.get("description"),
        "candidates": candidates,
        "error": None,
    }
    set_cached(cache_key, result)
    return result


def search_diseases(query: str, limit: int = 10) -> Dict[str, Any]:
    cache_key = f"open_targets:search_diseases:{query.lower()}:{limit}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    gql = """
    query SearchDiseases($query: String!, $size: Int!) {
      search(queryString: $query, entityNames: ["disease"], page: { index: 0, size: $size }) {
        hits {
          id
          name
          description
          entity
        }
      }
    }
    """
    payload = _graphql_query(gql, {"query": query, "size": limit})
    hits = payload.get("data", {}).get("search", {}).get("hits", [])
    results = [
        {
            "id": hit.get("id"),
            "name": hit.get("name"),
            "description": (hit.get("description") or "")[:300],
            "entity": hit.get("entity"),
            "source": SOURCE_NAME,
        }
        for hit in hits
        if hit.get("id") and hit.get("name")
    ]
    result = {"source": SOURCE_NAME, "available": bool(results), "query": query, "results": results, "error": None}
    set_cached(cache_key, result)
    return result


def search_genes(query: str, limit: int = 10) -> Dict[str, Any]:
    cache_key = f"open_targets:search_genes:{query.upper()}:{limit}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    gql = """
    query SearchGenes($query: String!, $size: Int!) {
      search(queryString: $query, entityNames: ["target"], page: { index: 0, size: $size }) {
        hits {
          id
          name
          description
          entity
        }
      }
    }
    """
    payload = _graphql_query(gql, {"query": query, "size": limit})
    hits = payload.get("data", {}).get("search", {}).get("hits", [])
    results = []
    for hit in hits:
        name = hit.get("name") or ""
        symbol = name.split(" - ")[0].strip() if " - " in name else name
        results.append(
            {
                "id": hit.get("id"),
                "symbol": symbol.upper() if symbol else symbol,
                "name": name,
                "description": (hit.get("description") or "")[:300],
                "ensembl_id": hit.get("id"),
                "source": SOURCE_NAME,
            }
        )
    result = {"source": SOURCE_NAME, "available": bool(results), "query": query, "results": results, "error": None}
    set_cached(cache_key, result)
    return result


def safe_search_diseases(query: str, limit: int = 10) -> Dict[str, Any]:
    if not query.strip():
        return {"source": SOURCE_NAME, "available": False, "query": query, "results": [], "error": "Empty query"}
    try:
        return search_diseases(query, limit=limit)
    except Exception as exc:  # noqa: BLE001
        return {"source": SOURCE_NAME, "available": False, "query": query, "results": [], "error": str(exc)}


def safe_search_genes(query: str, limit: int = 10) -> Dict[str, Any]:
    if not query.strip():
        return {"source": SOURCE_NAME, "available": False, "query": query, "results": [], "error": "Empty query"}
    try:
        return search_genes(query, limit=limit)
    except Exception as exc:  # noqa: BLE001
        return {"source": SOURCE_NAME, "available": False, "query": query, "results": [], "error": str(exc)}


def safe_fetch_disease_targets_by_id(efo_id: str, limit: int = 10) -> Dict[str, Any]:
    try:
        return fetch_disease_targets_by_id(efo_id, limit=limit)
    except Exception as exc:  # noqa: BLE001
        return {
            "source": SOURCE_NAME,
            "available": False,
            "disease_id": efo_id,
            "disease_name": efo_id,
            "candidates": [],
            "error": str(exc),
        }


def fetch_disease_targets(disease_key: str, limit: int = 10) -> Dict[str, Any]:
    """Return normalized disease-to-target associations from Open Targets."""
    disease_meta = normalize_disease(disease_key)
    efo_id = disease_meta["efo_id"]
    cache_key = f"open_targets:disease_targets:{efo_id}:{limit}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    query = """
    query DiseaseTargets($efoId: String!, $size: Int!) {
      disease(efoId: $efoId) {
        id
        name
        description
        associatedTargets(page: { index: 0, size: $size }) {
          count
          rows {
            score
            target {
              id
              approvedSymbol
              approvedName
            }
          }
        }
      }
    }
    """
    payload = _graphql_query(query, {"efoId": efo_id, "size": limit})
    disease = payload.get("data", {}).get("disease") or {}
    rows = disease.get("associatedTargets", {}).get("rows", [])

    candidates: List[Dict[str, Any]] = []
    for row in rows:
        target = row.get("target") or {}
        symbol = target.get("approvedSymbol")
        if not symbol:
            continue
        score = float(row.get("score") or 0.0)
        candidates.append(
            {
                "symbol": symbol,
                "score": round(score, 4),
                "ensembl_id": target.get("id"),
                "name": target.get("approvedName"),
                "reasons": [
                    f"Associated with {disease.get('name', disease_meta['label'])} in Open Targets",
                    f"Association score {score:.3f}",
                ],
                "source": SOURCE_NAME,
            }
        )

    result = {
        "source": SOURCE_NAME,
        "available": bool(candidates),
        "disease_id": disease.get("id") or efo_id,
        "disease_name": disease.get("name") or disease_meta["label"],
        "disease_description": disease.get("description"),
        "candidates": candidates,
        "error": None,
    }
    set_cached(cache_key, result)
    return result


def fetch_target_diseases(gene_symbol: str, limit: int = 5) -> Dict[str, Any]:
    """Return diseases associated with a target gene."""
    symbol = normalize_gene_symbol(gene_symbol)
    ensembl_id = get_ensembl_id(symbol)
    cache_key = f"open_targets:target_diseases:{ensembl_id}:{limit}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    if not ensembl_id:
        return {
            "source": SOURCE_NAME,
            "available": False,
            "gene_symbol": symbol,
            "diseases": [],
            "error": f"No Ensembl mapping for {symbol}",
        }

    query = """
    query TargetDiseases($ensemblId: String!, $size: Int!) {
      target(ensemblId: $ensemblId) {
        id
        approvedSymbol
        associatedDiseases(page: { index: 0, size: $size }) {
          rows {
            score
            disease {
              id
              name
            }
          }
        }
      }
    }
    """
    payload = _graphql_query(query, {"ensemblId": ensembl_id, "size": limit})
    target = payload.get("data", {}).get("target") or {}
    rows = target.get("associatedDiseases", {}).get("rows", [])

    diseases = [
        {
            "disease_id": row.get("disease", {}).get("id"),
            "disease_name": row.get("disease", {}).get("name"),
            "score": round(float(row.get("score") or 0.0), 4),
        }
        for row in rows
        if row.get("disease", {}).get("name")
    ]

    result = {
        "source": SOURCE_NAME,
        "available": bool(diseases),
        "gene_symbol": symbol,
        "ensembl_id": ensembl_id,
        "diseases": diseases,
        "error": None,
    }
    set_cached(cache_key, result)
    return result


def safe_fetch_target_diseases(gene_symbol: str, limit: int = 5) -> Dict[str, Any]:
    try:
        return fetch_target_diseases(gene_symbol, limit=limit)
    except Exception as exc:  # noqa: BLE001
        return {
            "source": SOURCE_NAME,
            "available": False,
            "gene_symbol": normalize_gene_symbol(gene_symbol),
            "diseases": [],
            "error": str(exc),
        }


def safe_fetch_disease_targets(disease_key: str, limit: int = 10) -> Dict[str, Any]:
    try:
        return fetch_disease_targets(disease_key, limit=limit)
    except Exception as exc:  # noqa: BLE001 - adapter must never crash callers
        return {
            "source": SOURCE_NAME,
            "available": False,
            "disease_id": normalize_disease(disease_key)["efo_id"],
            "disease_name": normalize_disease(disease_key)["label"],
            "candidates": [],
            "error": str(exc),
        }
