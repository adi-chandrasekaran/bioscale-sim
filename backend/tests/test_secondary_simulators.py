from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_evolution_uses_selected_gene_and_returns_clone_outputs():
    response = client.post("/api/evolution", json={
        "disease": "melanoma", "gene": "BRAF", "mutation": "p.V600E", "steps": 30,
        "initial_population": 10000, "starting_mutated_fraction": 0.08, "mutation_rate": 0.06,
        "immune_pressure": 0.5, "nutrient_level": 0.7, "stress_level": 0.4,
        "protein_activity": 0.8, "protein_stability": 0.7, "repair_capacity": 0.45,
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["clones"][0]["mutations"] == ["BRAF p.V600E"]
    assert payload["timeline"][-1]["step"] == 30
    assert {"Clone A", "Clone B", "Clone C"}.issubset(payload["summary"]["final_clone_fractions"])
    assert "Clone B" in payload["timeline"][-1]["clone_fractions"]
    assert any(clone["clone_name"] == "Clone B" for clone in payload["clones"])
    assert any(child["name"] == "Clone B" for child in payload["clone_tree"]["children"])
    assert any(child["name"] == "Clone B" for child in payload["final_composition"]["children"])
    clone_b_fraction = payload["summary"]["final_clone_fractions"]["Clone B"]
    clone_b_circle = next(child for child in payload["final_composition"]["children"] if child["name"] == "Clone B")
    assert clone_b_circle["value"] == clone_b_fraction


def test_evolution_simulate_supports_configurable_clone_count_and_reasoning():
    response = client.post("/api/evolution/simulate", json={
        "disease": "breast cancer",
        "disease_category": "cancer",
        "gene": "BRCA1",
        "mutation": "p.C61G",
        "steps": 48,
        "max_clone_count": 8,
        "initial_population": 25000,
        "starting_affected_fraction": 0.04,
        "mutation_rate": 0.08,
        "immune_pressure": 0.7,
        "nutrient_level": 0.45,
        "stress_level": 0.6,
        "protein_effect": {"protein_id": "P38398", "loss_of_function_score": 0.74},
        "alphafold_context": {"alphafold_available": True},
        "cell_phenotype": {"repair_capacity": 0.18, "genomic_instability": 0.82, "proliferation": 0.72},
        "pathway_node_activity": {"DNA_REPAIR": 0.2},
        "population_state": {"final_mutated_fraction": 0.55},
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    clones = payload["clones"]
    assert len(clones) == 8
    assert [clone["generation_order"] for clone in clones] == list(range(8))
    assert clones[0]["parent_clone_id"] is None
    assert all(clone["parent_clone_id"] for clone in clones[1:])
    assert all(clone["why_it_emerged"] for clone in clones)
    assert all(clone["why_it_expanded_or_declined"] for clone in clones)
    assert all(clone["biological_interpretation"] for clone in clones)
    assert "Clone B" in payload["timeline"][-1]["clone_fractions"]
    assert "Clone B" in payload["summary"]["final_clone_fractions"]
    assert any(event["clone_name"] == "Clone B" for event in payload["major_events"])
    assert abs(sum(payload["summary"]["final_clone_fractions"].values()) - 1.0) < 0.02
    assert payload["evidence_summary"]["database_evidence"] == ["UniProt", "AlphaFold DB", "Reactome"]


def test_evolution_missing_evidence_and_non_cancer_context_are_explicit():
    response = client.post("/api/evolution/simulate", json={
        "disease": "cystic fibrosis",
        "disease_category": "genetic disease",
        "gene": "CFTR",
        "mutation": "p.F508del",
        "steps": 24,
        "max_clone_count": 4,
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload["clones"]) == 4
    assert payload["evidence_summary"]["database_evidence"] == []
    assert any("No direct database evidence found" in item for item in payload["evidence_summary"]["missing_evidence"])
    assert "tumor" not in payload["student_explanation"].lower()


def test_intervention_modifies_baseline_and_returns_comparison():
    response = client.post("/api/intervention", json={
        "disease": "cancer", "gene": "TP53", "mutation": "p.R175H",
        "intervention_type": "Drug", "strength": 0.8, "target": "all mutated cells",
        "baseline_mutated_fraction": 0.6, "baseline_ecosystem_risk": 0.7,
        "proliferation": 0.9, "apoptosis": 0.2, "repair_capacity": 0.3, "immune_clearance": 0.4,
        "baseline_timeline": [{"step": 0, "mutated_fraction": 0.1}, {"step": 60, "mutated_fraction": 0.6}],
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["modified_biology"]["proliferation"] < 0.9
    assert payload["comparison"]["post_intervention_mutated_fraction"] < 0.6
    assert payload["timeline"][-1]["after"] < payload["timeline"][-1]["before"]


def test_intervention_drug_search_and_evidence_are_structured():
    search_response = client.get("/api/search/drugs", params={"q": "imatinib", "target": "ABL1"})
    assert search_response.status_code == 200, search_response.text
    search_payload = search_response.json()
    assert search_payload["results"]
    assert search_payload["results"][0]["label"].lower() == "imatinib"
    assert "ABL1" in search_payload["results"][0]["meta"]["known_targets"]

    evidence_response = client.get("/api/drug/evidence", params={"drug": "Gleevec", "gene": "ABL1"})
    assert evidence_response.status_code == 200, evidence_response.text
    evidence_payload = evidence_response.json()
    assert evidence_payload["normalized_drug"] == "imatinib"
    assert "ABL1" in evidence_payload["known_targets"]
    assert evidence_payload["mechanism"]


def test_intervention_build_fills_drug_mechanism_and_target():
    response = client.post("/api/intervention/build", json={
        "disease": "chronic myeloid leukemia",
        "gene": "ABL1",
        "mutation": "BCR-ABL1 fusion",
        "intervention_type": "Drug",
        "drug_name": "imatinib",
        "target": "ABL1",
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["suggested_target"] == "ABL1"
    assert "kinase" in payload["mechanism"].lower()
    assert payload["evidence"]["known_targets"]


def test_intervention_simulate_outputs_research_grade_fields_and_changes_with_inputs():
    base = {
        "disease": "chronic myeloid leukemia",
        "gene": "ABL1",
        "mutation": "BCR-ABL1 fusion",
        "intervention_type": "Drug",
        "drug_name": "imatinib",
        "target": "ABL1",
        "baseline_mutated_fraction": 0.65,
        "baseline_ecosystem_risk": 0.72,
        "proliferation": 0.88,
        "apoptosis": 0.18,
        "repair_capacity": 0.35,
        "immune_clearance": 0.42,
        "inflammation": 0.55,
        "stress_response": 0.6,
        "pathway_activity": 0.8,
        "pathway_disruption": 0.74,
        "clone_fitness": 0.75,
        "dominant_clone_fraction": 0.62,
        "baseline_timeline": [{"step": 0, "mutated_fraction": 0.2}, {"step": 60, "mutated_fraction": 0.65}],
    }
    low = client.post("/api/intervention/simulate", json={**base, "strength": 0.2})
    high = client.post("/api/intervention/simulate", json={**base, "strength": 0.85, "specificity": 0.9, "tissue_penetration": 0.86})
    assert low.status_code == 200, low.text
    assert high.status_code == 200, high.text
    low_payload = low.json()
    high_payload = high.json()
    assert high_payload["comparison"]["post_intervention_mutated_fraction"] < low_payload["comparison"]["post_intervention_mutated_fraction"]
    assert high_payload["comparison"]["net_effect"] > low_payload["comparison"]["net_effect"]
    assert high_payload["before_after_metrics"]
    assert high_payload["mechanism_graph"]["nodes"]
    assert high_payload["ecosystem_before_after"]["before"]["children"]
    assert high_payload["student_explanation"]["mechanism_of_action"]
    assert "not treatment advice" in high_payload["disclaimer"].lower()


def test_intervention_unknown_drug_does_not_crash_and_marks_missing_evidence():
    response = client.post("/api/intervention/simulate", json={
        "disease": "cancer",
        "gene": "TP53",
        "mutation": "p.R175H",
        "intervention_type": "Drug",
        "drug_name": "unknown research compound",
        "target": "TP53",
        "strength": 0.5,
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["evidence_summary"]["available"] is False
    assert payload["modified_biology"]["ecosystem_risk"] >= 0


def test_digital_twin_uses_profile_and_shared_baseline():
    response = client.post("/api/digital-twin", json={
        "disease": "melanoma", "gene": "BRAF", "mutation": "p.V600E", "protein": "B-Raf",
        "pathway": "MAPK signaling", "age": 62, "sex": "female", "weight_kg": 78, "height_cm": 165,
        "family_history": ["melanoma"], "smoking": "former", "exercise_minutes_week": 90,
        "diet_quality": 0.55, "genes": ["BRAF"], "mutations": ["p.V600E"],
        "laboratory_values": {"crp": 4.2},
        "baseline": {"ecosystem_risk": 0.58, "mutated_fraction": 0.31, "protein_activity": 0.72,
                     "repair_capacity": 0.42, "proliferation": 0.76, "immune_clearance": 0.38},
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mutation_interpretation"]["gene"] == "BRAF"
    assert payload["population_behaviour"]["mutated_fraction"] == 0.31
    assert 0 < payload["confidence"] <= 1
    assert payload["reasoning"]
    assert "diagnosis" in payload["disclaimer"].lower()


def test_patient_digital_twin_unknown_illness_ranks_without_disease_gene_mutation():
    response = client.post("/api/patient-digital-twin/rank-diseases", json={
        "mode": "unknown",
        "symptoms": "fatigue, fever, cough, shortness of breath",
        "age": 34,
        "sex": "female",
        "family_history": ["asthma"],
        "laboratory_values": {"crp": 12},
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "unknown"
    assert len(payload["differential_diagnosis"]) == 20
    assert payload["normalized_symptoms"]
    first = payload["differential_diagnosis"][0]
    assert {"rank", "disease", "disease_category", "matching_symptoms", "confidence", "why_ranked_here"}.issubset(first)
    assert payload["intervention_scenarios"][0]["selected_disease"] == first["disease"]
    assert "diagnosis" in payload["disclaimer"].lower()


def test_patient_digital_twin_known_disease_accepts_disease_and_symptoms_only():
    response = client.post("/api/patient-digital-twin/known-disease-model", json={
        "mode": "known",
        "disease": "asthma",
        "symptoms": "cough, shortness of breath, chest pain",
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "known"
    assert payload["known_disease_panels"]["Known Disease Mechanism"]
    assert payload["differential_diagnosis"][0]["disease"] == "asthma"
    assert payload["intervention_scenarios"][0]["selected_disease"] == "asthma"


def test_patient_digital_twin_known_disease_with_gene_mutation_and_red_flag():
    response = client.post("/api/patient-digital-twin/known-disease-model", json={
        "mode": "known",
        "disease": "coronary artery disease",
        "gene": "LDLR",
        "mutation": "p.G528D",
        "symptoms": "chest pain, shortness of breath",
        "variants": ["LDLR p.G528D"],
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mutation_interpretation"]["gene"] == "LDLR"
    assert payload["safety_warnings"]
    assert "treatment recommendation" in payload["disclaimer"].lower()


def test_simulation_includes_structured_causal_reasoning():
    response = client.post("/api/simulate", json={
        "disease_id": "EFO_0000311", "disease_name": "cancer", "gene": "BRCA1",
        "mutation": "p.V600E", "steps": 10, "use_external_evidence": False,
    })
    assert response.status_code == 200, response.text
    reasoning = response.json()["reasoning"]
    assert [step["layer"] for step in reasoning["steps"]] == [
        "Mutation", "Protein", "Pathway", "Cell", "Population", "Ecosystem"
    ]
    assert len(reasoning["causal_graph"]["edges"]) == 5
    assert all(0 <= step["confidence"] <= 1 for step in reasoning["steps"])
