from __future__ import annotations

from typing import Optional
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    AIChatRequest,
    AIChatResponse,
    AIStatusResponse,
    CandidateGene,
    NormalizedEvidence,
    SearchResponse,
    SearchResultItem,
    SimulationInputSummary,
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
    search_variants_endpoint,
)
from app.services.cell_simulator import simulate_cell
from app.services.population_simulator import simulate_population
from app.services.ecosystem_simulator import simulate_ecosystem

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


@app.post("/api/simulate", response_model=SimulationResult)
def simulate(req: SimulationRequest) -> SimulationResult:
    kb = load_knowledge_base()
    disease_id = req.disease_id
    disease_name = req.disease_name or req.disease or disease_id
    if req.disease and req.disease in kb.get("diseases", {}) and not req.disease_name:
        disease_name = kb["diseases"][req.disease]["label"]

    try:
        discovery, mutation, protein, pathway, evidence, external_available, notice = run_searchable_pipeline(
            kb,
            disease_id,
            disease_name,
            req.gene,
            req.mutation,
            req.use_external_evidence,
            req.pathway_id,
            req.pathway_name,
        )

        gene_symbol = req.gene
        selected = next((c for c in discovery.candidates if c.symbol == gene_symbol), None)
        if selected is None:
            selected = CandidateGene(
                symbol=gene_symbol,
                score=0.5,
                reasons=[f"User-selected gene {gene_symbol}"],
                source="User selection",
            )

        cell = simulate_cell(pathway)
        population = simulate_population(cell, req)
        ecosystem = simulate_ecosystem(cell, population, req)

        simulation_input = SimulationInputSummary(
            disease_name=disease_name,
            disease_id=disease_id,
            gene_symbol=gene_symbol,
            gene_id=evidence.gene.get("ensembl_id") if evidence else None,
            mutation=mutation.mutation,
            protein_accession=protein.protein_id,
            pathway_name=pathway.selected_pathway_name or pathway.label,
            pathway_id=pathway.selected_pathway_id or pathway.pathway_id,
            pathway_source=pathway.selected_pathway_source,
        )

        research_summary = (
            f"Selected {disease_name} ({disease_id}), gene {gene_symbol}, variant {mutation.mutation}. "
            f"Protein activity={protein.activity:.2f}, stability={protein.stability:.2f}, binding={protein.binding:.2f}. "
            f"Pathway disruptions={len(pathway.disrupted_processes)}. "
            f"Population mutated fraction={population.final_mutated_fraction:.2f}. "
            f"Ecosystem risk={ecosystem.ecosystem_risk_score:.2f}."
        )

        return SimulationResult(
            request=req,
            simulation_input=simulation_input,
            disease_discovery=discovery,
            selected_candidate=selected,
            mutation_result=mutation,
            protein_effect=protein,
            pathway_result=pathway,
            cell_phenotype=cell,
            population_result=population,
            ecosystem_result=ecosystem,
            research_summary=research_summary,
            citations=[{"name": s, "purpose": "database evidence"} for s in evidence.sources],
            external_evidence_available=external_available,
            evidence_notice=notice,
            evidence=evidence,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
