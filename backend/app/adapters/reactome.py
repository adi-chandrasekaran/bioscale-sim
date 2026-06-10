from __future__ import annotations

import requests

BASE_URL = "https://reactome.org/ContentService"


def fetch_pathways_for_uniprot(accession: str) -> list[dict]:
    """Fetch Reactome pathways for a UniProt accession. Optional connector; not used by offline demo."""
    response = requests.get(f"{BASE_URL}/data/pathways/low/entity/{accession}", timeout=20)
    response.raise_for_status()
    return response.json()
