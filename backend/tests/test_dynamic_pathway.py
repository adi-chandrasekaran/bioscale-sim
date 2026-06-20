from __future__ import annotations

import copy

from app.models import SimulationRequest
from app.services.cell_simulator import simulate_cell
from app.services.data_loader import load_knowledge_base
from app.services.ecosystem_simulator import simulate_ecosystem
from app.services.kb_builder import build_simulation_kb
from app.services.mutation_engine import interpret_mutation
from app.services.pathway_builder import P53_PATHWAY_KEY, build_dynamic_pathway, is_p53_demo_pathway
from app.services.pathway_simulator import simulate_pathway
from app.services.population_simulator import simulate_population
from app.services.protein_effect import predict_protein_effect


def _run_pipeline_for_gene(kb, gene: str, mutation: str):
    mutation_result = interpret_mutation(kb, gene, mutation) if gene == "TP53" else None
    if mutation_result is None:
        from app.adapters.normalizer import infer_multipliers_from_classification

        multipliers = infer_multipliers_from_classification("pathogenic")
        kb = copy.deepcopy(kb)
        kb.setdefault("mutations", {}).setdefault(gene, {})[mutation] = {
            "notation": mutation,
            "kind": "missense",
            "position": 600,
            "from_aa": "V",
            "to_aa": "E",
            "domain": "kinase domain",
            "biological_interpretation": f"Test mutation in {gene}",
            **multipliers,
        }
        kb.setdefault("genes", {}).setdefault(gene, {"name": gene, "protein_id": "TEST", "domains": []})
        mutation_result = interpret_mutation(kb, gene, mutation)

    protein = predict_protein_effect(kb, mutation_result)
    pathway = simulate_pathway(kb, protein)
    cell = simulate_cell(pathway)
    population = simulate_population(
        cell,
        SimulationRequest(gene=gene, mutation=mutation, steps=10),
    )
    ecosystem = simulate_ecosystem(
        cell,
        population,
        SimulationRequest(gene=gene, mutation=mutation, steps=10),
    )
    return mutation_result, protein, pathway, cell, population, ecosystem


def test_non_tp53_pathway_does_not_use_p53_demo_graph():
    local_kb = load_knowledge_base()
    pathway_key, pathway_dict, source = build_dynamic_pathway(
        "BRCA1",
        "P38398",
        "breast cancer",
        reactome={"available": True, "pathways": [{"stId": "R-HSA-123", "displayName": "DNA repair"}]},
        local_kb=local_kb,
    )
    assert pathway_key != P53_PATHWAY_KEY
    assert "BRCA1" in pathway_dict["nodes"]
    assert "TP53" not in pathway_dict["nodes"]
    assert source != "Local curated p53 demo model"


def test_changing_gene_changes_pathway_node_labels():
    local_kb = load_knowledge_base()
    _, tp53_pathway, _ = build_dynamic_pathway("TP53", "P04637", "cancer", local_kb=local_kb)
    _, brca_pathway, _ = build_dynamic_pathway("BRCA1", "P38398", "breast cancer", local_kb=local_kb)

    tp53_nodes = set(tp53_pathway["nodes"].keys())
    brca_nodes = set(brca_pathway["nodes"].keys())
    assert "TP53" in tp53_nodes
    assert "BRCA1" in brca_nodes
    assert tp53_nodes != brca_nodes


def test_tp53_demo_still_uses_p53_pathway_when_selected():
    local_kb = load_knowledge_base()
    key, pathway, source = build_dynamic_pathway("TP53", "P04637", "cancer", local_kb=local_kb)
    assert key == P53_PATHWAY_KEY
    assert is_p53_demo_pathway("TP53")
    assert "TP53" in pathway["nodes"]
    assert source == "Local curated p53 demo model"


def test_external_candidates_are_merged_with_local_disease_gene_set():
    local_kb = load_knowledge_base()
    kb = build_simulation_kb(
        local_kb,
        "EFO_0000311",
        "cancer",
        None,
        "TP53",
        "p.R175H",
        {"available": True, "candidates": [{"symbol": "TP53", "score": 0.95}]},
        {"available": False},
        {"available": True, "accession": "P04637", "protein_name": "p53", "domains": []},
        {"available": False},
    )

    genes = kb["diseases"]["selected_disease"]["known_genes"]
    assert len(genes) == 10
    assert "TP53" in genes
    assert "BRCA1" in genes


def test_card5_changes_when_pathway_output_changes():
    local_kb = load_knowledge_base()

    kb_tp53 = build_simulation_kb(
        local_kb, "EFO_0000311", "cancer", None, "TP53", "p.R175H",
        {"available": False, "candidates": []},
        {"available": False}, {"available": True, "accession": "P04637", "protein_name": "p53", "domains": []},
        {"available": False},
    )
    kb_brca = build_simulation_kb(
        local_kb, "EFO_0000311", "cancer", None, "BRCA1", "p.V600E",
        {"available": False, "candidates": []},
        {"available": False},
        {"available": True, "accession": "P38398", "protein_name": "BRCA1", "domains": []},
        {"available": False},
    )

    _, protein_tp53, pathway_tp53, cell_tp53, _, _ = _run_pipeline_for_gene(kb_tp53, "TP53", "p.R175H")
    _, protein_brca, pathway_brca, cell_brca, _, _ = _run_pipeline_for_gene(kb_brca, "BRCA1", "p.V600E")

    assert pathway_tp53.selected_gene == "TP53"
    assert pathway_brca.selected_gene == "BRCA1"
    assert pathway_tp53.pathway_id == P53_PATHWAY_KEY
    assert pathway_brca.pathway_id != P53_PATHWAY_KEY
    assert "TP53" in pathway_tp53.node_activities
    assert "BRCA1" in pathway_brca.node_activities
    assert "TP53" not in pathway_brca.node_activities
    assert cell_tp53.mapping_mode != cell_brca.mapping_mode or cell_tp53.proliferation_rate != cell_brca.proliferation_rate


def test_card6_changes_when_cell_phenotype_changes():
    local_kb = load_knowledge_base()
    kb = build_simulation_kb(
        local_kb, "EFO_0000311", "cancer", None, "TP53", "p.R175H",
        {"available": False, "candidates": []},
        {"available": False}, {"available": False}, {"available": False},
    )
    _, _, pathway, cell_low, _, _ = _run_pipeline_for_gene(kb, "TP53", "p.R175H")

    cell_high = copy.deepcopy(cell_low)
    cell_high.proliferation_rate = min(1.0, cell_low.proliferation_rate + 0.35)
    cell_high.apoptosis_rate = max(0.0, cell_low.apoptosis_rate - 0.20)

    pop_low = simulate_population(cell_low, SimulationRequest(gene="TP53", mutation="p.R175H", steps=10))
    pop_high = simulate_population(cell_high, SimulationRequest(gene="TP53", mutation="p.R175H", steps=10))

    assert pop_low.final_mutated_fraction != pop_high.final_mutated_fraction


def test_card7_changes_when_population_changes():
    local_kb = load_knowledge_base()
    kb = build_simulation_kb(
        local_kb, "EFO_0000311", "cancer", None, "TP53", "p.R175H",
        {"available": False, "candidates": []},
        {"available": False}, {"available": False}, {"available": False},
    )
    _, _, _, cell, pop_low, _ = _run_pipeline_for_gene(kb, "TP53", "p.R175H")

    pop_high = copy.deepcopy(pop_low)
    pop_high.final_mutated_fraction = min(1.0, pop_low.final_mutated_fraction + 0.25)
    pop_high.clonal_expansion_score = min(1.0, pop_low.clonal_expansion_score + 0.25)

    eco_low = simulate_ecosystem(cell, pop_low, SimulationRequest(gene="TP53", mutation="p.R175H", steps=10))
    eco_high = simulate_ecosystem(cell, pop_high, SimulationRequest(gene="TP53", mutation="p.R175H", steps=10))

    assert eco_low.ecosystem_risk_score != eco_high.ecosystem_risk_score


def test_tp53_r175h_pipeline_end_to_end_local():
    local_kb = load_knowledge_base()
    kb = build_simulation_kb(
        local_kb, "EFO_0000311", "cancer", None, "TP53", "p.R175H",
        {"available": False, "candidates": []},
        {"available": False}, {"available": False}, {"available": False},
    )
    mutation, protein, pathway, cell, population, ecosystem = _run_pipeline_for_gene(kb, "TP53", "p.R175H")

    assert mutation.gene == "TP53"
    assert mutation.mutation == "p.R175H"
    assert protein.loss_of_function_score > 0.4
    assert pathway.pathway_id == P53_PATHWAY_KEY
    assert pathway.selected_gene == "TP53"
    assert population.final_mutated_fraction >= 0
    assert 0 <= ecosystem.ecosystem_risk_score <= 1
