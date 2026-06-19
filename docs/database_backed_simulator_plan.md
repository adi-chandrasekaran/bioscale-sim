# Database-Backed Searchable Simulator Plan

BioScale Simulator has been upgraded from fixed dropdowns and `knowledge_base.json` into a **searchable, database-backed research prototype**. The local JSON file remains only as an offline fallback and teaching-graph model layer.

## User Experience

Users search like a research engine:

- **Disease**: breast cancer, Alzheimer, cystic fibrosis
- **Gene**: TP53, BRCA1, KRAS
- **Variant**: p.R175H, V600E, rs121913343, TP53 R175H
- **Pathway** (optional): Reactome pathways for the selected gene

Autocomplete queries hit backend search routes with caching. Users select exact entities before running the simulation.

## Databases Used

| Database | Role |
|----------|------|
| **Open Targets** | Disease search, gene/target search, disease–target association scores |
| **ClinVar (NCBI E-utilities)** | Variant search, clinical classification, phenotype links |
| **UniProt** | Protein accession, name, concise function, domains, mutation→domain mapping |
| **Reactome** | Pathway search, pathway IDs/names, gene membership, participants |

### Future databases (planned, not wired)

- gnomAD — population allele frequency
- COSMIC — somatic mutation catalog
- TCGA — tumor alteration prevalence
- AlphaFold — structural confidence
- STRING — protein–protein interactions
- Human Protein Atlas — tissue expression

## API Routes

| Route | Purpose |
|-------|---------|
| `GET /api/search/diseases?q=` | Autocomplete disease search |
| `GET /api/search/genes?q=` | Autocomplete gene search |
| `GET /api/search/variants?q=&gene=` | Autocomplete variant search |
| `GET /api/search/pathways?q=&gene=` | Pathway search / gene membership |
| `GET /api/evidence?disease_id=&gene_symbol=&mutation=` | Normalized evidence bundle |
| `POST /api/simulate` | Fetch evidence → summarize → run simulator |

## Card → Database Mapping

| Card | Database evidence | Simulator assumption | Computed output |
|------|-------------------|---------------------|-----------------|
| 1. Disease discovery | Open Targets disease + top 10 gene scores | Local fallback if API fails | Rank ordering |
| 2. Mutation engine | ClinVar classification, phenotypes | HGVS parser when ClinVar missing; activity multipliers | Amino-acid change text |
| 3. Protein effect | UniProt name, accession, function, domain hit | Activity/stability/binding scores; AlphaFold placeholder | Loss-of-function score |
| 4. Pathway simulator | Reactome pathway IDs, membership, participants | Graph nodes, edge weights, propagation rules | Node activities, disrupted processes |
| 5–7. Cell / population / ecosystem | — | Model parameters | All phenotype and risk scores |

## Data Provenance Labels

Every displayed value is tagged:

1. **External database evidence**
2. **Local fallback** (offline `knowledge_base.json`)
3. **Simulator assumption**
4. **Computed model output**

Raw API payloads appear only in collapsible **“View raw evidence”** sections.

## Summarization Rules

The `summarizer` layer enforces concise UI text:

- Protein function: max 3 sentences, citations stripped
- Gene association: max 2 sentences
- Mutation: max 3 sentences
- Pathway: max 3 sentences

## Limitations

- Not a diagnostic tool; ClinVar classes are research context only
- Pathway **graph simulation** remains a simplified teaching model
- Mutation effect multipliers are simulator assumptions unless locally curated (e.g. TP53 p.R175H demo)
- API rate limits and network failures trigger graceful fallback messages
- Genes without local teaching graphs still simulate using fallback pathway topology

## TP53 p.R175H Demo

The default search pre-fills **cancer / TP53 / p.R175H**. With external databases enabled, evidence comes from Open Targets, ClinVar, UniProt, and Reactome. With databases disabled or unavailable, the local curated fallback preserves the original demo behavior.

## Disclaimer

**Research prototype only, not a diagnostic tool.**
