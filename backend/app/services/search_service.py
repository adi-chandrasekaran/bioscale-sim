from __future__ import annotations

from typing import Any, Dict

from app.adapters.chembl import safe_search_drugs
from app.adapters.clinvar import safe_search_variants
from app.adapters.mondo_hpo import safe_search_phenotypes
from app.adapters.open_targets import safe_search_diseases, safe_search_genes
from app.adapters.reactome import safe_search_pathways
from app.adapters.uniprot import safe_search_genes_uniprot


def search_diseases_endpoint(query: str, limit: int = 10) -> Dict[str, Any]:
    return safe_search_diseases(query, limit=limit)


def search_genes_endpoint(query: str, limit: int = 10) -> Dict[str, Any]:
    ot = safe_search_genes(query, limit=limit)
    if ot.get("available"):
        return ot
    uni = safe_search_genes_uniprot(query, limit=limit)
    if uni.get("available"):
        return {
            "source": "UniProt",
            "available": True,
            "query": query,
            "results": [
                {
                    "id": row.get("accession"),
                    "symbol": row.get("symbol"),
                    "name": row.get("protein_name") or row.get("symbol"),
                    "description": f"UniProt {row.get('accession')}",
                    "accession": row.get("accession"),
                    "source": "UniProt",
                }
                for row in uni.get("results", [])
            ],
            "error": None,
        }
    return ot


def search_variants_endpoint(query: str, gene: str | None = None, limit: int = 10) -> Dict[str, Any]:
    return safe_search_variants(query, gene_symbol=gene, limit=limit)


def search_pathways_endpoint(query: str, gene: str | None = None, limit: int = 10) -> Dict[str, Any]:
    return safe_search_pathways(query, gene=gene, limit=limit)


def search_proteins_endpoint(query: str, limit: int = 10) -> Dict[str, Any]:
    payload = safe_search_genes_uniprot(query, limit=limit)
    return {
        **payload,
        "results": [
            {
                "id": row.get("accession"),
                "accession": row.get("accession"),
                "name": row.get("protein_name") or row.get("symbol") or query,
                "description": f"{row.get('symbol') or query} · {row.get('organism') or 'Homo sapiens'}",
                "symbol": row.get("symbol"),
                "source": row.get("source", "UniProt"),
            }
            for row in payload.get("results", [])
        ],
    }


def search_drugs_endpoint(query: str, target: str | None = None, limit: int = 10) -> Dict[str, Any]:
    return safe_search_drugs(query, target=target, limit=limit)


def search_phenotypes_endpoint(query: str, limit: int = 10) -> Dict[str, Any]:
    return safe_search_phenotypes(query, limit=limit)
