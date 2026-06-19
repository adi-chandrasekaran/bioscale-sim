from unittest.mock import patch

from fastapi.testclient import TestClient

from app.adapters.summarizer import limit_sentences, summarize_protein_function
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_diseases_route_structure():
    with patch("app.main.search_diseases_endpoint") as mock_search:
        mock_search.return_value = {
            "source": "Open Targets",
            "available": True,
            "query": "cancer",
            "results": [{"id": "EFO_0000311", "name": "cancer", "description": "test", "source": "Open Targets"}],
            "error": None,
        }
        response = client.get("/api/search/diseases", params={"q": "cancer"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["results"][0]["id"] == "EFO_0000311"
    assert payload["results"][0]["label"] == "cancer"


def test_search_genes_route_structure():
    with patch("app.main.search_genes_endpoint") as mock_search:
        mock_search.return_value = {
            "source": "Open Targets",
            "available": True,
            "query": "TP53",
            "results": [{"id": "ENSG00000141510", "symbol": "TP53", "name": "TP53", "source": "Open Targets"}],
            "error": None,
        }
        response = client.get("/api/search/genes", params={"q": "TP53"})
    assert response.status_code == 200
    assert response.json()["results"][0]["label"]


def test_search_variants_route_structure():
    with patch("app.main.search_variants_endpoint") as mock_search:
        mock_search.return_value = {
            "source": "ClinVar",
            "available": True,
            "query": "p.R175H",
            "results": [{"id": "123", "notation": "p.R175H", "title": "TP53 p.R175H", "classification": "pathogenic", "source": "ClinVar"}],
            "error": None,
        }
        response = client.get("/api/search/variants", params={"q": "p.R175H", "gene": "TP53"})
    assert response.status_code == 200
    assert response.json()["results"][0]["label"]


@patch("app.main.fetch_normalized_evidence")
def test_evidence_endpoint_returns_normalized_bundle(mock_fetch):
    from app.models import NormalizedEvidence

    mock_fetch.return_value = NormalizedEvidence(
        disease={"id": "EFO_0000311", "name": "cancer"},
        gene={"symbol": "TP53"},
        variant={"notation": "p.R175H"},
        protein={"accession": "P04637"},
        pathways=[],
        sources=["Open Targets"],
        summaries={"protein": "Short protein summary."},
        external_evidence_available=True,
    )
    response = client.get(
        "/api/evidence",
        params={"disease_id": "EFO_0000311", "gene_symbol": "TP53", "mutation": "p.R175H"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["gene"]["symbol"] == "TP53"
    assert payload["external_evidence_available"] is True


def test_simulation_pipeline_returns_all_layers_local_only():
    response = client.post(
        "/api/simulate",
        json={
            "disease_id": "EFO_0000311",
            "disease_name": "cancer",
            "gene": "TP53",
            "mutation": "p.R175H",
            "steps": 20,
            "use_external_evidence": False,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mutation_result"]["gene"] == "TP53"
    assert payload["protein_effect"]["loss_of_function_score"] > 0.4
    assert len(payload["pathway_result"]["nodes"]) > 0
    assert payload["disclaimer"] == "Research prototype only, not a diagnostic tool."
    assert "provenance" in payload["disease_discovery"]
    assert payload["mutation_result"]["summary"] is not None or payload["mutation_result"]["biological_interpretation"]


def test_simulation_pipeline_with_external_evidence_flag():
    response = client.post(
        "/api/simulate",
        json={
            "disease_id": "EFO_0000311",
            "gene": "TP53",
            "mutation": "p.R175H",
            "steps": 20,
            "use_external_evidence": True,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mutation_result"]["gene"] == "TP53"
    assert "external_evidence_available" in payload
    assert len(payload["disease_discovery"]["candidates"]) <= 10
    assert payload["protein_effect"]["provenance"]["activity"]["category"] == "simulator_assumption"


def test_unknown_mutation_gives_400():
    response = client.post(
        "/api/simulate",
        json={"disease_id": "EFO_0000311", "gene": "TP53", "mutation": "p.NOPE", "use_external_evidence": False},
    )
    assert response.status_code == 400


def test_uniprot_summarizer_not_huge():
    raw = (
        "Acts as a tumor suppressor. Induces cell cycle arrest. "
        "Involved in apoptosis. Binds DNA. {ECO:0000269|PubMed:12345} "
        "More detail here. Additional sentence. Extra sentence beyond limit."
    )
    summary = summarize_protein_function(raw, "p53")
    assert len(summary) < 500
    assert "PubMed" not in summary
    assert summary.count(".") <= 3


def test_limit_sentences_caps_output():
    text = "One. Two. Three. Four. Five."
    assert limit_sentences(text, 2) == "One. Two."


def test_clinvar_parser_for_r175h():
    from app.adapters.normalizer import amino_acid_change_text, parse_hgvs_protein

    parsed = parse_hgvs_protein("p.R175H")
    assert parsed is not None
    assert parsed["position"] == 175
    assert amino_acid_change_text("p.R175H") == "R→H at position 175"
