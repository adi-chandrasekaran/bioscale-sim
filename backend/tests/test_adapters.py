from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.adapters.clinvar import safe_fetch_variant_evidence, safe_search_variants
from app.adapters.normalizer import parse_hgvs_protein
from app.adapters.open_targets import safe_fetch_disease_targets, safe_search_diseases
from app.adapters.reactome import safe_fetch_pathway_evidence
from app.adapters.summarizer import known_gene_function, summarize_protein_function
from app.adapters.uniprot import resolve_uniprot_accession, safe_fetch_protein_evidence
from app.adapters.alphafold import get_structure_urls, safe_get_structure_status
from app.services.disease_discovery import discover_candidate_genes


OPEN_TARGETS_SEARCH = {
    "data": {
        "search": {
            "hits": [
                {"id": "EFO_0000311", "name": "cancer", "description": "A disease.", "entity": "disease"}
            ]
        }
    }
}

OPEN_TARGETS_RESPONSE = {
    "data": {
        "disease": {
            "id": "EFO_0000311",
            "name": "cancer",
            "description": "A disease involving uncontrolled cell growth.",
            "associatedTargets": {
                "count": 1,
                "rows": [
                    {
                        "score": 0.91,
                        "target": {
                            "id": "ENSG00000141510",
                            "approvedSymbol": "TP53",
                            "approvedName": "tumor protein p53",
                        },
                    }
                ],
            },
        }
    }
}


CLINVAR_SUMMARY = {
    "result": {
        "uids": ["12345"],
        "12345": {
            "uid": "12345",
            "title": "NM_000546.6(TP53):c.524G>A (p.Arg175His) Pathogenic",
            "germline_classification": {"description": "Pathogenic"},
            "trait_set": [{"trait_name": "Li-Fraumeni syndrome"}],
        },
    }
}


UNIPROT_RESPONSE = {
    "uniProtkbId": "P04637",
    "genes": [{"geneName": {"value": "TP53"}}],
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Cellular tumor antigen p53"}},
    },
    "comments": [
        {
            "commentType": "FUNCTION",
            "texts": [{"value": "Acts as a tumor suppressor in many tumor types. {ECO:0000269|PubMed:12345} More text."}],
        }
    ],
    "features": [
        {
            "type": "Domain",
            "description": "DNA-binding",
            "location": {"start": {"value": 102}, "end": {"value": 292}},
        }
    ],
    "organism": {"scientificName": "Homo sapiens"},
    "sequence": {"length": 393},
}


REACTOME_PATHWAYS = [
    {"stId": "R-HSA-109581", "displayName": "Apoptosis", "speciesName": "Homo sapiens"},
]


@patch("app.adapters.open_targets.requests.post")
@patch("app.adapters.open_targets.get_cached", return_value=None)
@patch("app.adapters.open_targets.set_cached")
def test_open_targets_search(mock_set_cache, mock_get_cache, mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = OPEN_TARGETS_SEARCH
    mock_post.return_value = mock_response

    from app.adapters.open_targets import search_diseases

    result = search_diseases("cancer")
    assert result["available"] is True
    assert result["results"][0]["id"] == "EFO_0000311"


@patch("app.adapters.open_targets.requests.post")
@patch("app.adapters.open_targets.get_cached", return_value=None)
@patch("app.adapters.open_targets.set_cached")
def test_open_targets_adapter(mock_set_cache, mock_get_cache, mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = OPEN_TARGETS_RESPONSE
    mock_post.return_value = mock_response

    result = safe_fetch_disease_targets("cancer", limit=10)
    assert result["available"] is True
    assert result["candidates"][0]["symbol"] == "TP53"


@patch("app.adapters.open_targets.requests.post", side_effect=RuntimeError("network down"))
@patch("app.adapters.open_targets.get_cached", return_value=None)
def test_open_targets_adapter_failure(mock_get_cache, mock_post):
    result = safe_search_diseases("cancer")
    assert result["available"] is False


@patch("app.adapters.clinvar._fetch_clinvar_summaries")
@patch("app.adapters.clinvar._search_clinvar_ids", return_value=["12345"])
@patch("app.adapters.clinvar.get_cached", return_value=None)
@patch("app.adapters.clinvar.set_cached")
def test_clinvar_adapter(mock_set_cache, mock_get_cache, mock_search, mock_fetch):
    mock_fetch.return_value = [CLINVAR_SUMMARY["result"]["12345"]]
    result = safe_fetch_variant_evidence("TP53", "p.R175H")
    assert result["available"] is True
    assert result["clinvar_classification"] == "pathogenic"


@patch("app.adapters.clinvar.requests.get", side_effect=RuntimeError("timeout"))
@patch("app.adapters.clinvar.get_cached", return_value=None)
def test_clinvar_variant_search_fallback_parser(mock_get_cache, mock_get):
    result = safe_search_variants("p.R175H", gene_symbol="TP53")
    assert result["available"] is True
    assert result["results"][0]["notation"] == "p.R175H"


@patch("app.adapters.uniprot._fetch_json", return_value=UNIPROT_RESPONSE)
@patch("app.adapters.uniprot.get_cached", return_value=None)
@patch("app.adapters.uniprot.set_cached")
def test_uniprot_adapter_and_summarizer(mock_set_cache, mock_get_cache, mock_fetch):
    result = safe_fetch_protein_evidence("TP53", mutation_position=175)
    assert result["available"] is True
    summary = summarize_protein_function(result["function_raw"], result["protein_name"])
    assert len(summary) < 500
    assert "PubMed" not in summary


@patch("app.adapters.uniprot.search_genes_uniprot")
def test_uniprot_resolver_uses_live_gene_search_before_local_fallback(mock_search):
    mock_search.return_value = {
        "available": True,
        "results": [
            {
                "symbol": "KRAS",
                "accession": "P01116",
                "protein_name": "GTPase KRas",
            }
        ],
    }

    result = resolve_uniprot_accession("KRAS", local_kb={})

    assert result["accession"] == "P01116"
    assert result["resolution_source"] == "uniprot_gene_search"


def test_uniprot_resolver_accepts_typed_accession():
    result = resolve_uniprot_accession("TP53", requested_accession="p04637")

    assert result["accession"] == "P04637"
    assert result["resolution_source"] == "typed_protein_accession"


def test_curated_gene_functions_cover_common_candidate_genes_without_demo_placeholder():
    for symbol in ["MET", "MSH6", "RET", "RB1", "KRAS", "EGFR", "BRCA1", "BRCA2"]:
        summary = known_gene_function(symbol)
        assert summary
        assert "local demo" not in summary.lower()


def test_local_candidate_discovery_uses_gene_function_for_generated_candidates():
    kb = {
        "diseases": {
            "selected_disease": {
                "label": "cancer",
                "affected_cell_context": "tumor context",
                "known_genes": ["MSH2", "RET"],
                "candidate_gene_weights": {"MSH2": 0.93, "RET": 0.93},
            }
        },
        "genes": {},
    }

    result = discover_candidate_genes(kb, "selected_disease")

    summaries = {candidate.symbol: candidate.function_summary for candidate in result.candidates}
    assert "mismatch repair" in summaries["MSH2"].lower()
    assert "receptor tyrosine kinase" in summaries["RET"].lower()
    assert all("local demo" not in (summary or "").lower() for summary in summaries.values())


@patch("app.adapters.reactome._fetch_json")
@patch("app.adapters.reactome.get_cached", return_value=None)
@patch("app.adapters.reactome.set_cached")
def test_reactome_adapter(mock_set_cache, mock_get_cache, mock_fetch):
    mock_fetch.side_effect = [REACTOME_PATHWAYS, []]
    result = safe_fetch_pathway_evidence("TP53")
    assert result["available"] is True
    assert result["pathways"][0]["stId"] == "R-HSA-109581"


def test_normalizer_hgvs_parser():
    parsed = parse_hgvs_protein("p.R175H")
    assert parsed is not None
    assert parsed["position"] == 175


def test_normalizer_maps_known_ensembl_ids_back_to_symbols():
    from app.adapters.normalizer import normalize_gene_symbol

    assert normalize_gene_symbol("ENSG00000141510") == "TP53"


def test_normalizer_infers_coding_variant_type():
    from app.adapters.normalizer import infer_variant_type_from_notation

    assert infer_variant_type_from_notation("c.5946delT") in {"coding deletion", "coding variant"}


def test_alphafold_url_builder_is_deterministic():
    urls = get_structure_urls("P04637")
    assert urls["pdb_url"].endswith("AF-P04637-F1-model_v4.pdb")
    assert urls["mmcif_url"].endswith("AF-P04637-F1-model_v4.cif")
    assert urls["pae_url"].endswith("AF-P04637-F1-predicted_aligned_error_v4.json")


@patch("app.adapters.alphafold.requests.get", side_effect=RuntimeError("offline"))
def test_alphafold_status_fails_closed(mock_get):
    status = safe_get_structure_status("CACHEMISS_TEST_ACCESSION", position=175)
    assert status["alphafold_available"] is False
    assert status["confidence_label"] == "unavailable"
