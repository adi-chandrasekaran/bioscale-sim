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
    assert set(payload["summary"]["final_clone_fractions"]) == {"Clone A", "Clone B", "Clone C"}


def test_intervention_modifies_baseline_and_returns_comparison():
    response = client.post("/api/intervention", json={
        "disease": "cancer", "gene": "TP53", "mutation": "p.R175H",
        "intervention_type": "Growth inhibitor", "strength": 0.8, "target": "all mutated cells",
        "baseline_mutated_fraction": 0.6, "baseline_ecosystem_risk": 0.7,
        "proliferation": 0.9, "apoptosis": 0.2, "repair_capacity": 0.3, "immune_clearance": 0.4,
        "baseline_timeline": [{"step": 0, "mutated_fraction": 0.1}, {"step": 60, "mutated_fraction": 0.6}],
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["modified_biology"]["proliferation"] < 0.9
    assert payload["comparison"]["post_intervention_mutated_fraction"] < 0.6
    assert payload["timeline"][-1]["after"] < payload["timeline"][-1]["before"]
