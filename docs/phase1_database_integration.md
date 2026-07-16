# Phase 1 Database Integration

BioScale Simulator Phase 1 connects the first four pipeline cards to public biological databases while preserving the local `knowledge_base.json` as a fallback. The TP53 `p.R175H` demo continues to run even when external APIs are unavailable.

## Databases Used

| Database | Adapter | API |
|----------|---------|-----|
| Open Targets Platform | `app/adapters/open_targets.py` | GraphQL `https://api.platform.opentargets.org/api/v4/graphql` |
| ClinVar (NCBI) | `app/adapters/clinvar.py` | E-utilities `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` |
| UniProt | `app/adapters/uniprot.py` | REST `https://rest.uniprot.org/uniprotkb/` |
| Reactome | `app/adapters/reactome.py` | Content Service `https://reactome.org/ContentService/` |
| AlphaFold DB | `app/adapters/alphafold.py` | Metadata/API + deterministic structure URLs |

### Future adapters (stubs only)

These adapters return structured unavailable states until the source is fully wired or licensing/credential questions are resolved:

- STRING — protein-protein interactions
- gnomAD — population allele frequencies
- Human Protein Atlas — tissue expression
- GTEx — normal tissue expression
- cBioPortal and GDC/TCGA — public cancer cohort evidence
- CIViC — cancer variant evidence statements
- ChEMBL and PharmGKB — intervention and pharmacogenomic evidence
- MONDO/HPO — disease and phenotype ontology
- OMIM and COSMIC — licensed sources; no scraping
- ClinGen — gene-disease validity

## Which Card Each Database Supports

| Card | Primary external source | What is real evidence | What remains a model assumption |
|------|-------------------------|----------------------|--------------------------------|
| 1. Disease discovery | Open Targets | Disease name, top gene associations, association scores | Disease context text, pathway/interaction bonuses for genes missing from Open Targets |
| 2. Mutation engine | ClinVar | Variant records, clinical classification, linked phenotypes | Activity/stability/binding multipliers, confidence, biological interpretation text |
| 3. Protein effect | UniProt + AlphaFold DB | Accession, protein name, function text, domain features, AlphaFold availability and structure URLs | Activity/stability/binding scores, loss-of-function score, residue highlighting |
| 4. Pathway simulator | Reactome | Pathway IDs/names, participant membership | Node baselines, edge weights, activity propagation, disrupted-process thresholds |

Cards 5–7 (cell, population, ecosystem) remain pure simulator output.

## API Endpoints

### `GET /api/evidence`

Query parameters: `disease`, `gene`, `mutation`

Returns a single JSON bundle with normalized evidence from all adapters, plus cache-friendly metadata.

### `POST /api/simulate`

Request fields related to external evidence:

```json
{
  "use_external_evidence": true,
  "protein_accession": "P04637",
  "protein_name": "Cellular tumor antigen p53"
}
```

When `true` (default), the backend fetches external evidence, merges it into a copy of the local knowledge base, runs the existing simulators, and enriches the response with provenance metadata.

When `false`, only `knowledge_base.json` is used.

If a protein accession is supplied by the UI protein selector, the backend treats it as the strongest identifier. If not, the backend resolves the typed gene through UniProt gene search, then local mappings as a last fallback.

If any adapter fails, the response includes:

> External evidence unavailable; using local curated model.

The request never crashes because of adapter failures.

## Data Provenance Labels

Every value in cards 1–4 is tagged with one of five provenance categories:

1. **External database evidence** — fetched from Open Targets, ClinVar, UniProt, or Reactome
2. **Local curated knowledge** — from `backend/data/knowledge_base.json`
3. **Simulator assumption** — curated parameters or placeholders (e.g. mutation multipliers, AlphaFold TODO)
4. **Computed model output** — derived by parsers or simulation layers (e.g. loss-of-function score, pathway node activities)
5. **Missing/unavailable evidence** — an adapter exists but no source data is available yet

The frontend renders these as colored badges on each field.

## Source Status

Simulation responses include `simulation_input.source_status` and `evidence.source_status`. Each external source is marked with one of:

- `available` — source returned usable evidence
- `not_found` — source was reachable but did not have matching evidence
- `input_unresolved` — the user input could not be resolved to the identifier that source needs
- `api_unavailable` — source failed or timed out
- `fallback_used` — local curated data or simulator fallback was used intentionally

## Caching

Responses are cached in `backend/cache/` as JSON files keyed by SHA-256 hashes. Default TTL is 24 hours. This reduces repeated calls during development and demos.

## Normalization

`app/adapters/normalizer.py` and the public-source adapters map:

- Local disease keys → Open Targets EFO IDs
- Gene symbols → Ensembl IDs and last-resort default UniProt accessions
- UniProt accessions → AlphaFold IDs and structure URLs
- HGVS protein notation → ClinVar search terms and amino-acid change text
- Reactome payloads → stable pathway ID/name dictionaries

UniProt accession resolution now uses this order:

1. User-selected or typed UniProt accession
2. HGNC symbol/alias lookup and HGNC UniProt mappings
3. UniProt gene search for a reviewed human protein match
4. Local `knowledge_base.json` mapping as the final fallback

AlphaFold DB is queried from the resolved UniProt accession, so it is no longer limited to the TP53 demo case.

When AlphaFold DB has no public structure, the structure panel now continues the evidence chain:

1. RCSB PDB / UniProt PDB cross-references
2. UniProt protein domains, regions, and sequence features
3. A checked-not-found source audit only after those sources fail

Every evidence source can report:

- `available`
- `procured_from_secondary_source`
- `model_inferred_from_source`
- `checked_not_found`
- `api_unreachable`
- `input_unresolved`

## Limitations

- **Not a diagnostic tool.** ClinVar classifications and Open Targets scores are shown for research context only.
- **Evidence procurement before fallback.** Unknown or rare inputs first query HGNC, UniProt, Open Targets, ClinVar, CIViC, Reactome, AlphaFold DB, and structure-feature sources where relevant. Simulator fallback is shown only after the checked source chain cannot provide that evidence.
- **Simplified pathway graph.** Reactome provides membership evidence; if Reactome cannot produce a usable pathway, the graph falls back to a dynamic gene-centered teaching model.
- **Mutation effect multipliers** remain locally curated even when ClinVar returns a pathogenic classification.
- **Rate limits.** NCBI E-utilities and public APIs may throttle or fail; the fallback path is always available.
- **Neurodegeneration demo genes** (APOE, TREM2, etc.) have disease metadata but limited local mutation/pathway data.

## Intervention Color Semantics

Intervention before/after metrics keep `direction`, `delta`, and `magnitude`, but now also include:

- `semantic_effect`: `beneficial`, `harmful`, or `neutral`
- `semantic_explanation`: why that direction is biologically interpreted that way

The frontend colors intervention bars by semantic effect, not raw increase/decrease. For example, reduced proliferation can be green because it is beneficial in the modeled disease context, while increased toxicity is red.

## Running Tests

```bash
cd backend
pytest -q
```

Adapter tests use mocked HTTP responses and do not require network access.

## Disclaimer

The UI displays: **"This is a research prototype, not a diagnostic tool."**

Do not use this system for clinical decision-making.
