from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_catalog_contains_cancer_and_tp53():
    response = client.get("/api/catalog")
    assert response.status_code == 200
    payload = response.json()
    assert any(d["key"] == "cancer" for d in payload["diseases"])
    assert any(g["symbol"] == "TP53" for g in payload["genes"])


def test_simulation_pipeline_returns_all_layers():
    response = client.post(
        "/api/simulate",
        json={
            "disease": "cancer",
            "gene": "TP53",
            "mutation": "p.R175H",
            "steps": 20,
            "initial_mutated_fraction": 0.02,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mutation_result"]["gene"] == "TP53"
    assert payload["protein_effect"]["loss_of_function_score"] > 0.4
    assert len(payload["pathway_result"]["nodes"]) > 0
    assert payload["cell_phenotype"]["genomic_instability"] >= 0
    assert len(payload["population_result"]["trajectory"]) == 21
    assert 0 <= payload["ecosystem_result"]["ecosystem_risk_score"] <= 1


def test_unknown_mutation_gives_400():
    response = client.post(
        "/api/simulate",
        json={"disease": "cancer", "gene": "TP53", "mutation": "p.NOPE"},
    )
    assert response.status_code == 400
