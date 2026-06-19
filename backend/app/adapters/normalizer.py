from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

# Local disease keys → Open Targets disease identifiers (EFO preferred).
DISEASE_ID_MAP: Dict[str, Dict[str, str]] = {
    "cancer": {
        "efo_id": "EFO_0000311",
        "label": "cancer",
        "search_term": "cancer",
    },
    "neurodegeneration": {
        "efo_id": "EFO_0002508",
        "label": "neurodegenerative disease",
        "search_term": "neurodegenerative disease",
    },
}

# Gene symbol → Ensembl gene ID (human, GRCh38) for Open Targets lookups.
GENE_ENSEMBL_MAP: Dict[str, str] = {
    "TP53": "ENSG00000141510",
    "MDM2": "ENSG00000135679",
    "CDKN1A": "ENSG00000124762",
    "BAX": "ENSG00000087088",
    "ATM": "ENSG00000149311",
    "APOE": "ENSG00000130203",
    "TREM2": "ENSG00000095970",
    "MAPT": "ENSG00000186868",
    "APP": "ENSG00000142192",
}

# Gene symbol → default UniProt accession (human).
GENE_UNIPROT_MAP: Dict[str, str] = {
    "TP53": "P04637",
    "MDM2": "Q00987",
    "CDKN1A": "P38936",
    "BAX": "Q07812",
    "ATM": "Q13315",
    "APOE": "P02649",
    "TREM2": "Q9NZC2",
    "MAPT": "P10636",
    "APP": "P05067",
}

HGVS_PROTEIN_RE = re.compile(
    r"^p\.(?P<from>[A-Z\*])(?P<pos>\d+)(?P<to>[A-Z\*])$", re.IGNORECASE
)
SHORT_PROTEIN_RE = re.compile(r"^(?P<from>[A-Z\*])(?P<pos>\d+)(?P<to>[A-Z\*])$", re.IGNORECASE)
GENE_VARIANT_RE = re.compile(
    r"^(?:(?P<gene>[A-Z0-9]+)\s+)?(?P<variant>p?\.?[A-Z\*]\d+[A-Z\*]|[A-Z]\d+[A-Z]|rs\d+)$",
    re.IGNORECASE,
)
RSID_RE = re.compile(r"^rs\d+$", re.IGNORECASE)


def normalize_disease(disease_key: str) -> Dict[str, str]:
    return DISEASE_ID_MAP.get(
        disease_key,
        {"efo_id": "", "label": disease_key, "search_term": disease_key.replace("_", " ")},
    )


def normalize_gene_symbol(gene_symbol: str) -> str:
    return gene_symbol.strip().upper()


def get_ensembl_id(gene_symbol: str) -> Optional[str]:
    return GENE_ENSEMBL_MAP.get(normalize_gene_symbol(gene_symbol))


def get_uniprot_accession(gene_symbol: str, local_kb: Optional[Dict[str, Any]] = None) -> Optional[str]:
    symbol = normalize_gene_symbol(gene_symbol)
    if local_kb:
        gene = local_kb.get("genes", {}).get(symbol, {})
        if gene.get("protein_id"):
            return gene["protein_id"]
    return GENE_UNIPROT_MAP.get(symbol)


def parse_hgvs_protein(notation: str) -> Optional[Dict[str, Any]]:
    text = notation.strip()
    match = HGVS_PROTEIN_RE.match(text)
    if not match:
        match = SHORT_PROTEIN_RE.match(text.lstrip("p."))
    if not match:
        return None
    return {
        "from_aa": match.group("from").upper(),
        "to_aa": match.group("to").upper(),
        "position": int(match.group("pos")),
        "notation": notation if text.startswith("p.") else f"p.{match.group('from').upper()}{match.group('pos')}{match.group('to').upper()}",
    }


def normalize_variant_query(query: str, gene_symbol: Optional[str] = None) -> Dict[str, Any]:
    text = query.strip()
    parsed_gene = None
    variant_text = text

    if " " in text:
        parts = text.split()
        if len(parts) >= 2 and parts[0].isalpha():
            parsed_gene = normalize_gene_symbol(parts[0])
            variant_text = " ".join(parts[1:])

    parsed = parse_hgvs_protein(variant_text.replace(" ", ""))
    if not parsed and not variant_text.startswith("p."):
        parsed = parse_hgvs_protein(variant_text)

    return {
        "gene_symbol": gene_symbol or parsed_gene,
        "query": text,
        "variant_text": variant_text,
        "parsed": parsed,
        "is_rsid": bool(RSID_RE.match(variant_text)),
        "notation": parsed["notation"] if parsed else variant_text,
    }


def infer_multipliers_from_classification(classification: Optional[str]) -> Dict[str, float]:
    if not classification:
        return {"activity_multiplier": 0.45, "stability_multiplier": 0.60, "binding_multiplier": 0.45, "confidence": 0.45}
    value = classification.lower()
    if "pathogenic" in value and "likely" not in value:
        return {"activity_multiplier": 0.25, "stability_multiplier": 0.50, "binding_multiplier": 0.25, "confidence": 0.70}
    if "likely pathogenic" in value:
        return {"activity_multiplier": 0.35, "stability_multiplier": 0.55, "binding_multiplier": 0.30, "confidence": 0.65}
    if "benign" in value:
        return {"activity_multiplier": 0.90, "stability_multiplier": 0.92, "binding_multiplier": 0.88, "confidence": 0.55}
    return {"activity_multiplier": 0.55, "stability_multiplier": 0.65, "binding_multiplier": 0.50, "confidence": 0.40}


def hgvs_to_clinvar_query(gene_symbol: str, notation: str) -> str:
    parsed = parse_hgvs_protein(notation)
    symbol = normalize_gene_symbol(gene_symbol)
    if not parsed:
        return f"{symbol}[Gene]"
    pos = parsed["position"]
    from_aa = parsed["from_aa"]
    to_aa = parsed["to_aa"]
    return f'{symbol}[Gene] AND "{from_aa}{pos}{to_aa}"[Variant name]'


def amino_acid_change_text(notation: str) -> Optional[str]:
    parsed = parse_hgvs_protein(notation)
    if not parsed:
        return None
    return f"{parsed['from_aa']}→{parsed['to_aa']} at position {parsed['position']}"


def normalize_clinvar_classification(raw: str) -> str:
    value = raw.strip().lower()
    mapping = {
        "benign": "benign",
        "likely benign": "likely benign",
        "uncertain significance": "VUS",
        "uncertain": "VUS",
        "vus": "VUS",
        "likely pathogenic": "likely pathogenic",
        "pathogenic": "pathogenic",
        "conflicting interpretations of pathogenicity": "VUS",
    }
    for key, label in mapping.items():
        if key in value:
            return label
    return raw or "unknown"


def merge_dicts(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def normalize_reactome_pathway(pathway: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "stId": pathway.get("stId") or pathway.get("dbId"),
        "displayName": pathway.get("displayName") or pathway.get("name"),
        "species": pathway.get("speciesName"),
        "isInDisease": pathway.get("isInDisease", False),
    }
