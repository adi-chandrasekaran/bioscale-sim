# Hardcoded Model Audit — TP53 / p53 Pathway Removal

**Date:** 2026-06-12  
**Scope:** Full backend + frontend search for `TP53`, `p53`, `MDM2`, `CDKN1A`, `BAX`, `ATM`, `DNA_REPAIR`, `APOPTOSIS`, `CELL_CYCLE_ARREST`, `PROLIFERATION_SIGNAL`, and `p53_damage_response`.

## Summary

The simulator previously defaulted every gene/disease/mutation selection to the curated `p53_damage_response` teaching graph. Cards 4–7 then read p53-specific node activities regardless of user input.

**Fix:** Selection-aware pathway building (`pathway_builder.py`), active-pathway routing (`kb_builder.py`, `pathway_simulator.py`), dual-mode cell phenotype mapping (`cell_simulator.py`), provenance passthrough (Cards 5–7), frontend reset + input summary, and seven new dynamic-pathway tests.

The TP53 `p.R175H` demo remains available when TP53 is explicitly selected and no non-p53 Reactome pathway overrides it.

---

## Allowed Locations (TP53 demo / reference data only)

These references are **intentional** and do not affect non-TP53 simulations.

| Location | Purpose | Verdict |
|----------|---------|---------|
| `backend/data/knowledge_base.json` | Curated TP53 demo: genes, mutations (`p.R175H`), `p53_damage_response` graph with TP53/MDM2/CDKN1A/BAX/ATM nodes | **Allowed** — loaded only when `is_p53_demo_pathway()` is true |
| `backend/app/services/pathway_builder.py` | `P53_DEMO_GENE`, `P53_PATHWAY_KEY`, `is_p53_demo_pathway()`, gated load of curated graph | **Allowed** — explicit TP53 demo gate |
| `backend/app/adapters/normalizer.py` | Static Ensembl/UniProt ID maps for TP53, MDM2, CDKN1A, BAX, ATM | **Allowed** — identifier lookup table, not simulation logic |
| `backend/app/models.py` | `SimulationRequest` defaults `gene=TP53`, `mutation=p.R175H` | **Allowed** — API/demo defaults only; overridden by user selection |
| `backend/app/main.py` | Evidence endpoint default query `gene_symbol=TP53` | **Allowed** — demo default for `/api/evidence` |
| `frontend/src/main.tsx` | `DEFAULT_GENE`, placeholder text, `initialQuery="TP53"` | **Allowed** — initial UI demo state; cleared on selection change |
| `backend/tests/test_*.py` | TP53 fixtures for adapter/search/demo regression tests | **Allowed** — test data |
| `backend/cache/*.json` | Cached Open Targets / ClinVar / UniProt / Reactome API responses | **Allowed** — external data cache, not code paths |

---

## Changed Locations (was affecting general simulations)

### Backend

| File | Before | After |
|------|--------|-------|
| `backend/app/services/kb_builder.py` | Assigned `p53_damage_response` to all genes via static KB `pathways` list | Calls `build_dynamic_pathway()` per selected gene; sets `active_pathway_key` on gene entry |
| `backend/app/services/pathway_builder.py` | *(new)* | Builds Reactome-informed or generic gene-centered graphs; returns curated p53 graph **only** when `is_p53_demo_pathway()` |
| `backend/app/services/pathway_simulator.py` | Hardcoded `p53_damage_response`; perturbed TP53 node always | Reads `active_pathway_key`; perturbs **selected gene** node using `protein_effect.activity`; returns `selected_gene`, `selected_protein`, `node_activities`, `baseline_activities`, `changed_nodes`, `is_generic_fallback`, provenance fields |
| `backend/app/services/cell_simulator.py` | Always used DNA_REPAIR / APOPTOSIS / CELL_CYCLE_ARREST / PROLIFERATION_SIGNAL | Uses p53-specific nodes **only if present** in current pathway; otherwise maps generic traits (`pathway_disruption_score`, `functional_loss_score`, `stress_signal`, `survival_signal`, `proliferation_signal`, `repair_or_homeostasis_capacity`) |
| `backend/app/services/population_simulator.py` | Independent of selection context | Passes `computed_from_gene/pathway/protein_activity` from cell phenotype |
| `backend/app/services/ecosystem_simulator.py` | Independent of selection context | Uses current cell + population; passes through `computed_from_*` |
| `backend/app/services/evidence_service.py` | Local-only path reused static KB pathways | Local-only path also calls `build_dynamic_pathway()`; `_build_pathway()` attaches Reactome metadata and `computed_from_*` |
| `backend/app/models.py` | Minimal pathway/cell models | Extended `PathwayResult`, `CellPhenotypeResult`, `PopulationResult`, `EcosystemResult` with selection metadata; added `SimulationInputSummary` on `SimulationResult` |
| `backend/app/main.py` | Pipeline without input summary | `POST /api/simulate` builds `simulation_input` from selected disease/gene/mutation/protein/pathway |

### Frontend

| File | Before | After |
|------|--------|-------|
| `frontend/src/PathwayGraph.tsx` | Hardcoded TP53 node x/y positions (TP53, MDM2, CDKN1A, BAX, ATM, etc.) | Dynamic horizontal layout from node index and type; no gene-specific coordinates |
| `frontend/src/main.tsx` | Stale results after re-selection; no input summary | `resetSimulationState()` on disease/gene/variant/pathway change; **Current simulation input** panel; generic-pathway notice on Card 4; **Computed from** provenance lines on Cards 4–7 |
| `frontend/src/types.ts` | Old API shapes | Updated for `simulation_input`, `computed_from_*`, `is_generic_fallback`, generic cell traits |
| `frontend/src/style.css` | — | Styles for input summary panel and provenance lines |

### Tests (new)

| File | Coverage |
|------|----------|
| `backend/tests/test_dynamic_pathway.py` | Non-TP53 → no p53 demo graph; gene change → different node labels; Card 5–7 cascade; TP53 `p.R175H` end-to-end |

---

## Remaining References by Symbol

### `TP53` / `p53`

| Location | Affects general sim? | Notes |
|----------|---------------------|-------|
| `knowledge_base.json` | No (gated) | Demo KB content |
| `pathway_builder.py` | No (gated) | `P53_DEMO_GENE = "TP53"` |
| `cell_simulator.py` | No (gated) | `has_p53_nodes` branch only when DNA_REPAIR etc. exist in **current** pathway |
| `normalizer.py` | No | ID map |
| `models.py`, `main.py`, `main.tsx` | No | Defaults / placeholders |
| Tests | No | Regression fixtures |

### `MDM2`, `CDKN1A`, `BAX`, `ATM`

| Location | Affects general sim? | Notes |
|----------|---------------------|-------|
| `knowledge_base.json` | No (gated) | Nodes in curated `p53_damage_response` only |
| `normalizer.py` | No | ID map |
| `backend/cache/*` | No | API response data |

### `DNA_REPAIR`, `APOPTOSIS`, `CELL_CYCLE_ARREST`, `PROLIFERATION_SIGNAL`

| Location | Affects general sim? | Notes |
|----------|---------------------|-------|
| `knowledge_base.json` | No (gated) | Process nodes in curated p53 graph |
| `cell_simulator.py` | **Conditional** | Used only when these node IDs appear in the **active** pathway result — correct behavior for TP53 demo; skipped for generic graphs |

### `p53_damage_response`

| Location | Affects general sim? | Notes |
|----------|---------------------|-------|
| `knowledge_base.json` | No (gated) | Curated pathway key |
| `pathway_builder.py` | No (gated) | `P53_PATHWAY_KEY`; returned only via `is_p53_demo_pathway()` |

---

## Data Flow (post-fix)

```
User selection (disease, gene, mutation, pathway)
        ↓
build_simulation_kb() → build_dynamic_pathway() → active_pathway_key on gene
        ↓
interpret_mutation() → predict_protein_effect()
        ↓
simulate_pathway() — perturbs selected gene node with protein activity
        ↓
simulate_cell() — p53 nodes OR generic traits from current pathway
        ↓
simulate_population() ← cell phenotype
        ↓
simulate_ecosystem() ← cell + population
        ↓
SimulationResult + simulation_input summary → frontend Cards 1–7
```

---

## Verification

```bash
cd backend && python -m pytest tests/ -v   # 26 passed
cd frontend && npm run build               # succeeds
```

Manual check: select BRCA1 (or any non-TP53 gene) → Card 4 shows `BRCA1`, `FUNCTIONAL_PROCESS_*`, `CELL_OUTCOME` (not TP53/MDM2/CDKN1A/BAX/ATM). Select TP53 + `p.R175H` → Card 4 shows curated p53 damage response graph.

---

## Future Work (not in scope)

- Build Reactome edge-direction graphs when API provides usable topology (currently membership → generic centered graph).
- AlphaFold structural mapping placeholder in protein effect card.
- Expand local KB mutations beyond TP53 for offline-only mode without inferred multipliers.
