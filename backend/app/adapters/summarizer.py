from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

CITATION_RE = re.compile(r"\{ECO:\d+\|PubMed:\d+\}|\{ECO:[^}]+\}|PubMed:\d+|ECO:\d+\|PubMed:\d+")
WHITESPACE_RE = re.compile(r"\s+")


def strip_citations(text: str) -> str:
    cleaned = CITATION_RE.sub("", text)
    return WHITESPACE_RE.sub(" ", cleaned).strip()


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", strip_citations(text))
    return [p.strip() for p in parts if p.strip()]


def limit_sentences(text: str, max_sentences: int) -> str:
    if not text:
        return ""
    sentences = _split_sentences(text)
    return " ".join(sentences[:max_sentences])


def summarize_protein_function(raw_function: Optional[str], protein_name: str = "") -> str:
    if not raw_function:
        name = protein_name or "This protein"
        return f"No curated UniProt function text was retrieved for {name}; the simulator uses gene and variant context to infer protein impact."
    summary = limit_sentences(raw_function, 3)
    if len(summary) > 420:
        summary = summary[:417].rsplit(" ", 1)[0] + "..."
    return summary


def summarize_gene_association(gene_symbol: str, gene_name: str, score: float, disease_name: str) -> str:
    label = gene_name or gene_symbol
    return (
        f"{label} ({gene_symbol}) is associated with {disease_name} in Open Targets "
        f"with score {score:.2f}."
    )


def summarize_mutation(
    gene: str,
    notation: str,
    variant_type: str,
    aa_change: Optional[str],
    classification: Optional[str],
    from_clinvar: bool,
) -> str:
    parts: List[str] = []
    if aa_change:
        parts.append(f"The variant {notation} in {gene} changes {aa_change}.")
    else:
        parts.append(f"The variant {notation} in {gene} was submitted for simulation.")
    if variant_type and variant_type != "unknown":
        parts.append(f"It is classified as a {variant_type} change.")
    if from_clinvar and classification and classification != "unknown":
        parts.append(f"ClinVar reports: {classification}.")
    elif not from_clinvar:
        parts.append("No external ClinVar classification was found; HGVS parsing was used.")
    return limit_sentences(" ".join(parts), 3)


def summarize_disease_fallback(disease_name: str) -> str:
    text = disease_name.strip() or "selected disease"
    return limit_sentences(
        f"No direct database disease text was retrieved for {text}; the simulator uses the selected disease label and associated gene context as a fallback.",
        2,
    )


def summarize_gene_fallback(gene_symbol: str, disease_name: str) -> str:
    return limit_sentences(
        f"{gene_symbol} is treated as the selected gene for {disease_name}. When database association scores are missing, the simulator uses the gene symbol, pathway links, and variant effect to continue the analysis.",
        2,
    )


def summarize_variant_fallback(gene_symbol: str, notation: str, variant_type: str) -> str:
    kind = variant_type if variant_type != "unknown" else "variant"
    return limit_sentences(
        f"The {kind} {notation} in {gene_symbol} is retained as a typed input and interpreted with HGVS parsing plus fallback rules when database records are unavailable.",
        2,
    )


def summarize_pathway_fallback(gene_symbol: str) -> str:
    return limit_sentences(
        f"No direct pathway match was retrieved, so the simulator generated a gene-centered fallback pathway around {gene_symbol} to keep downstream cards populated.",
        2,
    )


def summarize_protein_fallback(protein_name: str, gene_symbol: str) -> str:
    label = protein_name or gene_symbol
    return limit_sentences(
        f"{label} has no curated protein function text in the current evidence bundle, so the simulator infers protein impact from gene identity, variant class, and pathway context.",
        2,
    )


def summarize_pathway(pathway_name: str, pathway_id: str, gene_symbol: str) -> str:
    return limit_sentences(
        f"Reactome lists {pathway_name} ({pathway_id}) as a pathway involving {gene_symbol}. "
        "Membership is database evidence; edge dynamics in the simulator graph are model assumptions.",
        3,
    )


def summarize_functional_impact(
    gene: str,
    domain_hit: Optional[str],
    classification: Optional[str],
    activity: float,
) -> str:
    domain_text = f" in {domain_hit}" if domain_hit else ""
    class_text = f" ClinVar class: {classification}." if classification and classification != "unknown" else ""
    return limit_sentences(
        f"The simulator estimates reduced {gene} activity{domain_text} after the variant perturbation.{class_text} "
        f"Remaining activity score is {activity:.2f} (simulator assumption).",
        3,
    )


def build_card_summaries(evidence: Dict[str, Any]) -> Dict[str, str]:
    disease = evidence.get("disease", {})
    gene = evidence.get("gene", {})
    variant = evidence.get("variant", {})
    protein = evidence.get("protein", {})
    pathways = evidence.get("pathways", [])

    disease_name = disease.get("name") or disease.get("label") or "selected disease"
    gene_symbol = gene.get("symbol") or "gene"
    gene_name = gene.get("name") or gene_symbol

    pathway_summary = ""
    if pathways:
        primary = pathways[0]
        pathway_summary = summarize_pathway(
            primary.get("displayName") or primary.get("name") or "pathway",
            primary.get("stId") or primary.get("id") or "",
            gene_symbol,
        )

    return {
        "disease": limit_sentences(disease.get("summary") or disease.get("description") or summarize_disease_fallback(disease_name), 2),
        "gene": summarize_gene_association(
            gene_symbol,
            gene_name,
            float(gene.get("association_score") or 0.0),
            disease_name,
        ) if gene.get("association_score") else limit_sentences(gene.get("summary") or summarize_gene_fallback(gene_symbol, disease_name), 2),
        "mutation": (
            variant.get("summary")
            or (
                summarize_mutation(
                    gene_symbol,
                    variant.get("notation") or "",
                    variant.get("variant_type") or "unknown",
                    variant.get("amino_acid_change"),
                    variant.get("clinvar_classification"),
                    bool(variant.get("clinvar_available")),
                )
                if variant.get("notation")
                else summarize_variant_fallback(
                    gene_symbol,
                    "",
                    variant.get("variant_type") or "unknown",
                )
            )
        ),
        "protein": protein.get("summary") or (
            summarize_protein_function(protein.get("function_raw"), protein.get("name") or "")
            if protein.get("function_raw")
            else summarize_protein_fallback(protein.get("name") or "", gene_symbol)
        ),
        "pathway": pathway_summary or evidence.get("summary") or summarize_pathway_fallback(gene_symbol),
        "functional_impact": summarize_functional_impact(
            gene_symbol,
            protein.get("domain_hit"),
            variant.get("clinvar_classification"),
            float(protein.get("activity") or 0.5),
        ),
    }
