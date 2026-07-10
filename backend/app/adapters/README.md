# Real biology data adapters

The MVP uses a tiny local knowledge base so the demo works offline.

These adapters show where real data sources fit later:

- Open Targets: disease-to-target evidence and gene prioritization.
- UniProt: protein function, domains, sequence information.
- STRING: protein-protein interactions.
- Reactome: pathway membership and pathway graph data.
- ClinVar: variant classification and phenotype links.
- AlphaFold DB: precomputed structure availability, structure URLs, and confidence status.
- gnomAD, HPA, GTEx, cBioPortal, GDC, CIViC, ChEMBL, PharmGKB, MONDO/HPO, OMIM, COSMIC, and ClinGen are represented as explicit adapters or stubs. Stubs return a structured unavailable state instead of fake scientific evidence.

For a high-school research MVP, the correct strategy is not to rebuild these expert databases. Use them as sources, then focus your originality on the linked multi-scale simulator.
