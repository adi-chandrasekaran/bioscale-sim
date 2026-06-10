from __future__ import annotations

from typing import Any, Dict

from app.models import MutationResult


def interpret_mutation(kb: Dict[str, Any], gene_symbol: str, mutation_key: str) -> MutationResult:
    gene_mutations = kb.get("mutations", {}).get(gene_symbol, {})
    if mutation_key not in gene_mutations:
        available = list(gene_mutations.keys())
        raise ValueError(f"Unknown mutation '{mutation_key}' for {gene_symbol}. Available: {available}")

    mutation = gene_mutations[mutation_key]
    gene = kb["genes"][gene_symbol]

    explanation = (
        f"The {gene_symbol} DNA sequence is transcribed into RNA, and the RNA is translated into the "
        f"{gene['name']} protein. This variant is modeled as a {mutation['kind']} change. "
    )
    if mutation.get("position"):
        explanation += (
            f"At amino-acid position {mutation['position']}, {mutation.get('from_aa')} is replaced by "
            f"{mutation.get('to_aa')}. The change sits in the {mutation['domain']}, so the simulator treats it "
            "as a protein-function perturbation rather than a neutral spelling change."
        )
    else:
        explanation += "It is represented as a broad loss-of-function state without a specific amino-acid position."

    return MutationResult(
        gene=gene_symbol,
        mutation=mutation["notation"],
        kind=mutation["kind"],
        position=mutation.get("position"),
        domain=mutation["domain"],
        dna_rna_protein_explanation=explanation,
        biological_interpretation=mutation["biological_interpretation"],
        activity_multiplier=mutation["activity_multiplier"],
        stability_multiplier=mutation["stability_multiplier"],
        binding_multiplier=mutation["binding_multiplier"],
        confidence=mutation["confidence"],
    )
