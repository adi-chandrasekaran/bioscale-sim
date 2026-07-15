from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

if __package__ and __package__.startswith("backend."):
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    AIChatRequest,
    AIChatResponse,
    AIStatusResponse,
    NormalizedEvidence,
    SearchResponse,
    SearchResultItem,
    SimulationRequest,
    SimulationResult,
)
from app.services.data_loader import load_knowledge_base
from app.services.ai_assistant import answer_question, ai_status
from app.services.evidence_service import fetch_normalized_evidence, run_searchable_pipeline
from app.services.search_service import (
    search_diseases_endpoint,
    search_genes_endpoint,
    search_pathways_endpoint,
    search_drugs_endpoint,
    search_phenotypes_endpoint,
    search_variants_endpoint,
    search_proteins_endpoint,
)
from app.services.simulation_service import run_simulation
from app.services.reasoning_service import build_reasoning
from app.services.evolution_service import EvolutionRequest, EvolutionResult, simulate_evolution
from app.services.intervention_service import InterventionRequest, InterventionResult, simulate_intervention
from app.services.intervention_evidence_service import fetch_intervention_evidence
from app.services.digital_twin_service import (
    DigitalTwinRequest,
    DigitalTwinResult,
    build_digital_twin,
    build_known_disease_model,
    rank_diseases,
)
from app.adapters.alphafold import build_alphafold_summary, fetch_pdb_text

app = FastAPI(
    title="BioScale Simulator API",
    version="0.3.0",
    description="Database-backed searchable biology simulator.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "BIOSCALE_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _to_search_response(payload: dict) -> SearchResponse:
    results = [
        SearchResultItem(
            id=str(item.get("id") or item.get("stId") or item.get("symbol") or item.get("accession") or ""),
            label=item.get("name") or item.get("symbol") or item.get("displayName") or item.get("title") or item.get("notation") or "",
            subtitle=item.get("description") or item.get("classification") or item.get("protein_name"),
            description=item.get("description") or item.get("summary") or item.get("detail"),
            synonyms=item.get("synonyms", []) if isinstance(item.get("synonyms"), list) else [],
            normalized_mapping=item.get("normalized_mapping", {}) if isinstance(item.get("normalized_mapping"), dict) else {},
            source=item.get("source") or payload.get("source", "Unknown"),
            meta=item,
        )
        for item in payload.get("results", [])
        if item
    ]
    return SearchResponse(
        query=payload.get("query", ""),
        source=payload.get("source", "Unknown"),
        available=payload.get("available", False),
        results=results,
        error=payload.get("error"),
    )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "bioscale-simulator"}


@app.get("/api/catalog")
def catalog() -> dict:
    """Legacy catalog endpoint; search endpoints are preferred."""
    kb = load_knowledge_base()
    return {
        "diseases": [
            {"key": key, "label": value["label"], "description": value["description"]}
            for key, value in kb["diseases"].items()
        ],
        "genes": [
            {"symbol": key, "name": value["name"], "mutations": list(kb.get("mutations", {}).get(key, {}).keys())}
            for key, value in kb["genes"].items()
        ],
        "pathways": [
            {"key": key, "label": value["label"], "description": value["description"]}
            for key, value in kb["pathways"].items()
        ],
    }


@app.get("/api/search/diseases", response_model=SearchResponse)
def search_diseases(q: str = Query(min_length=1), limit: int = Query(default=10, le=25)) -> SearchResponse:
    return _to_search_response(search_diseases_endpoint(q, limit=limit))


@app.get("/api/search/genes", response_model=SearchResponse)
def search_genes(q: str = Query(min_length=1), limit: int = Query(default=10, le=25)) -> SearchResponse:
    return _to_search_response(search_genes_endpoint(q, limit=limit))


@app.get("/api/search/variants", response_model=SearchResponse)
def search_variants(
    q: str = Query(min_length=1),
    gene: Optional[str] = Query(default=None),
    limit: int = Query(default=10, le=25),
) -> SearchResponse:
    return _to_search_response(search_variants_endpoint(q, gene=gene, limit=limit))


@app.get("/api/search/pathways", response_model=SearchResponse)
def search_pathways(
    q: str = Query(default=""),
    gene: Optional[str] = Query(default=None),
    limit: int = Query(default=10, le=25),
) -> SearchResponse:
    if not q and not gene:
        return SearchResponse(query="", source="Reactome", available=False, results=[], error="Provide q or gene")
    return _to_search_response(search_pathways_endpoint(q, gene=gene, limit=limit))


@app.get("/api/search/proteins", response_model=SearchResponse)
def search_proteins(q: str = Query(min_length=1), limit: int = Query(default=10, le=25)) -> SearchResponse:
    return _to_search_response(search_proteins_endpoint(q, limit=limit))


@app.get("/api/search/drugs", response_model=SearchResponse)
def search_drugs(
    q: str = Query(min_length=1),
    target: Optional[str] = Query(default=None),
    limit: int = Query(default=10, le=25),
) -> SearchResponse:
    return _to_search_response(search_drugs_endpoint(q, target=target, limit=limit))


@app.get("/api/drug/evidence")
def drug_evidence(
    drug: str = Query(min_length=1),
    gene: Optional[str] = Query(default=""),
    mutation: Optional[str] = Query(default=""),
) -> dict:
    return fetch_intervention_evidence(drug, gene or "", mutation or "")


@app.get("/api/search/phenotypes", response_model=SearchResponse)
def search_phenotypes(q: str = Query(min_length=1), limit: int = Query(default=10, le=25)) -> SearchResponse:
    return _to_search_response(search_phenotypes_endpoint(q, limit=limit))


@app.get("/api/evidence", response_model=NormalizedEvidence)
def evidence(
    disease_id: str = Query(default="EFO_0000311"),
    gene_symbol: str = Query(default="TP53"),
    mutation: str = Query(default="p.R175H"),
    disease_name: Optional[str] = Query(default="cancer"),
    pathway_id: Optional[str] = Query(default=None),
    pathway_name: Optional[str] = Query(default=None),
) -> NormalizedEvidence:
    kb = load_knowledge_base()
    return fetch_normalized_evidence(
        disease_id,
        disease_name or disease_id,
        gene_symbol,
        mutation,
        kb,
        pathway_id=pathway_id,
        pathway_name=pathway_name,
    )


@app.get("/api/structure/alphafold")
def alphafold_structure(
    uniprot_accession: str = Query(min_length=1),
    position: Optional[int] = Query(default=None, ge=1),
    mutation: Optional[str] = Query(default=None),
) -> dict:
    return build_alphafold_summary(uniprot_accession, position=position, mutation=mutation)


@app.get("/api/structure/alphafold/pdb")
def alphafold_pdb_proxy(uniprot_accession: str = Query(min_length=1)) -> Response:
    try:
        pdb_text = fetch_pdb_text(uniprot_accession)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"AlphaFold PDB could not be loaded: {exc}") from exc
    if not pdb_text:
        raise HTTPException(status_code=404, detail="AlphaFold PDB text was empty or unavailable.")
    return Response(content=pdb_text, media_type="chemical/x-pdb")


@app.post("/api/simulate", response_model=SimulationResult)
def simulate(req: SimulationRequest) -> SimulationResult:
    try:
        return run_simulation(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/evolution", response_model=EvolutionResult)
def evolution(req: EvolutionRequest) -> EvolutionResult:
    return simulate_evolution(req)


@app.post("/api/evolution/simulate", response_model=EvolutionResult)
def evolution_simulate(req: EvolutionRequest) -> EvolutionResult:
    return simulate_evolution(req)


@app.post("/api/intervention", response_model=InterventionResult)
def intervention(req: InterventionRequest) -> InterventionResult:
    return simulate_intervention(req)


@app.post("/api/intervention/build")
def intervention_build(req: InterventionRequest) -> dict:
    evidence = fetch_intervention_evidence(req.drug_name or "", req.gene, req.mutation) if req.drug_name else {
        "available": False,
        "known_targets": [],
        "mechanism": "Non-drug or generic mechanism-based intervention.",
        "source_summaries": [],
    }
    return {
        "request": req.model_dump(),
        "evidence": evidence,
        "suggested_target": (evidence.get("known_targets") or [req.target])[0],
        "mechanism": evidence.get("mechanism", "Generic mechanism-based intervention"),
        "disclaimer": "Research simulation only — not treatment advice.",
    }


@app.post("/api/intervention/simulate", response_model=InterventionResult)
def intervention_simulate(req: InterventionRequest) -> InterventionResult:
    return simulate_intervention(req)


@app.post("/api/digital-twin", response_model=DigitalTwinResult)
def digital_twin(req: DigitalTwinRequest) -> DigitalTwinResult:
    return build_digital_twin(req)


@app.post("/api/patient-digital-twin/rank-diseases", response_model=DigitalTwinResult)
def patient_digital_twin_rank_diseases(req: DigitalTwinRequest) -> DigitalTwinResult:
    return rank_diseases(req)


@app.post("/api/patient-digital-twin/known-disease-model", response_model=DigitalTwinResult)
def patient_digital_twin_known_disease_model(req: DigitalTwinRequest) -> DigitalTwinResult:
    return build_known_disease_model(req)


@app.post("/api/reasoning")
def reasoning(result: SimulationResult) -> dict:
    return build_reasoning(result)


@app.post("/api/ai/chat", response_model=AIChatResponse)
def ai_chat(req: AIChatRequest) -> AIChatResponse:
    try:
        payload = answer_question(req.question, [turn.model_dump() for turn in req.history], req.context)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AIChatResponse(**payload)


@app.get("/api/ai/status", response_model=AIStatusResponse)
def ai_status_endpoint() -> AIStatusResponse:
    return AIStatusResponse(**ai_status())
