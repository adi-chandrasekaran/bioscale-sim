from __future__ import annotations

from app.models import CandidateGene, SimulationInputSummary, SimulationRequest, SimulationResult
from app.services.cell_simulator import simulate_cell
from app.services.data_loader import load_knowledge_base
from app.services.ecosystem_simulator import simulate_ecosystem
from app.services.evidence_service import run_searchable_pipeline
from app.services.population_simulator import simulate_population
from app.services.reasoning_service import build_reasoning


def run_simulation(req: SimulationRequest) -> SimulationResult:
    kb = load_knowledge_base()
    disease_id = req.disease_id
    disease_name = req.disease_name or req.disease or disease_id
    if req.disease and req.disease in kb.get("diseases", {}) and not req.disease_name:
        disease_name = kb["diseases"][req.disease]["label"]

    discovery, mutation, protein, pathway, evidence, external_available, notice = run_searchable_pipeline(
        kb, disease_id, disease_name, req.gene, req.mutation, req.use_external_evidence, req.pathway_id, req.pathway_name,
    )
    gene_symbol = req.gene
    selected = next((candidate for candidate in discovery.candidates if candidate.symbol == gene_symbol), None)
    if selected is None:
        selected = CandidateGene(symbol=gene_symbol, score=0.5, reasons=[f"User-selected gene {gene_symbol}"], source="User selection")

    cell = simulate_cell(pathway)
    population = simulate_population(cell, req)
    ecosystem = simulate_ecosystem(cell, population, req)
    alphafold = evidence.protein.get("alphafold", {}) if evidence else {}
    clinvar_ids = evidence.variant.get("clinvar_ids", []) if evidence else []
    source_status = {
        "Open Targets": "available" if "Open Targets" in evidence.sources else "missing/unavailable",
        "ClinVar": "available" if mutation.external_evidence_available else "missing/unavailable",
        "UniProt": "available" if protein.external_evidence_available else "missing/unavailable",
        "Reactome": "available" if pathway.external_evidence_available else "missing/unavailable",
        "AlphaFold DB": "available" if alphafold.get("alphafold_available") else "missing/unavailable",
    }
    simulation_input = SimulationInputSummary(
        disease_name=disease_name, disease_id=disease_id, gene_symbol=gene_symbol,
        gene_id=evidence.gene.get("ensembl_id") if evidence else None,
        uniprot_accession=protein.protein_id,
        protein_name=protein.protein_name,
        mutation=mutation.mutation,
        hgvs_notation=mutation.mutation,
        clinvar_variation_id=str(clinvar_ids[0]) if clinvar_ids else None,
        rsid=evidence.variant.get("rsid") if evidence else None,
        protein_accession=protein.protein_id,
        alphafold_available=bool(alphafold.get("alphafold_available")),
        alphafold_confidence_label=alphafold.get("confidence_label"),
        pathway_name=pathway.selected_pathway_name or pathway.label,
        pathway_id=pathway.selected_pathway_id or pathway.pathway_id, pathway_source=pathway.selected_pathway_source,
        data_source_status=source_status,
    )
    result = SimulationResult(
        request=req, simulation_input=simulation_input, disease_discovery=discovery, selected_candidate=selected,
        mutation_result=mutation, protein_effect=protein, pathway_result=pathway, cell_phenotype=cell,
        population_result=population, ecosystem_result=ecosystem,
        research_summary=(f"Selected {disease_name} ({disease_id}), gene {gene_symbol}, variant {mutation.mutation}. "
                          f"Protein activity={protein.activity:.2f}, stability={protein.stability:.2f}, binding={protein.binding:.2f}. "
                          f"Pathway disruptions={len(pathway.disrupted_processes)}. Population mutated fraction={population.final_mutated_fraction:.2f}. "
                          f"Ecosystem risk={ecosystem.ecosystem_risk_score:.2f}."),
        citations=[{"name": source, "purpose": "database evidence"} for source in evidence.sources],
        external_evidence_available=external_available, evidence_notice=notice, evidence=evidence,
    )
    result.reasoning = build_reasoning(result)
    return result
