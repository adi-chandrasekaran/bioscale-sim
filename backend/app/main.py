from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import SimulationRequest, SimulationResult
from app.services.data_loader import load_knowledge_base
from app.services.disease_discovery import discover_candidate_genes
from app.services.mutation_engine import interpret_mutation
from app.services.protein_effect import predict_protein_effect
from app.services.pathway_simulator import simulate_pathway
from app.services.cell_simulator import simulate_cell
from app.services.population_simulator import simulate_population
from app.services.ecosystem_simulator import simulate_ecosystem

app = FastAPI(
    title="BioScale Simulator API",
    version="0.1.0",
    description="A modular multi-scale biology simulator: disease gene -> mutation -> protein -> pathway -> cell -> population -> ecosystem.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "bioscale-simulator"}


@app.get("/api/catalog")
def catalog() -> dict:
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


@app.post("/api/simulate", response_model=SimulationResult)
def simulate(req: SimulationRequest) -> SimulationResult:
    kb = load_knowledge_base()
    try:
        discovery = discover_candidate_genes(kb, req.disease)
        gene_symbol = req.gene or discovery.candidates[0].symbol
        selected = next((c for c in discovery.candidates if c.symbol == gene_symbol), None)
        if selected is None:
            # Allow direct simulation of a gene in the KB even if not in this disease list.
            if gene_symbol not in kb["genes"]:
                raise ValueError(f"Unknown gene '{gene_symbol}'.")
            selected = discovery.candidates[0]

        mutation_key = req.mutation or "loss_of_function"
        mutation = interpret_mutation(kb, gene_symbol, mutation_key)
        protein = predict_protein_effect(kb, mutation)
        pathway = simulate_pathway(kb, protein)
        cell = simulate_cell(pathway)
        population = simulate_population(cell, req)
        ecosystem = simulate_ecosystem(cell, population, req)

        research_summary = (
            f"For {req.disease}, the system selected {gene_symbol} and modeled {mutation.mutation}. "
            f"The protein layer estimated activity={protein.activity}, stability={protein.stability}, "
            f"and binding={protein.binding}. The pathway layer identified {len(pathway.disrupted_processes)} "
            f"major process disruptions. The cell layer predicted proliferation={cell.proliferation_rate}, "
            f"apoptosis={cell.apoptosis_rate}, and genomic instability={cell.genomic_instability}. "
            f"After {req.steps} population steps, the mutated fraction reached {population.final_mutated_fraction}. "
            f"The ecosystem risk score was {ecosystem.ecosystem_risk_score}."
        )

        return SimulationResult(
            request=req,
            disease_discovery=discovery,
            selected_candidate=selected,
            mutation_result=mutation,
            protein_effect=protein,
            pathway_result=pathway,
            cell_phenotype=cell,
            population_result=population,
            ecosystem_result=ecosystem,
            research_summary=research_summary,
            citations=[
                {"name": "UniProt", "purpose": "protein sequence and function adapter target"},
                {"name": "Open Targets", "purpose": "disease-target evidence adapter target"},
                {"name": "Reactome", "purpose": "pathway knowledge adapter target"},
                {"name": "STRING", "purpose": "protein interaction adapter target"},
            ],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
