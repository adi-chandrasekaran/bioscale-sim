from __future__ import annotations

import requests

BASE_URL = "https://rest.uniprot.org/uniprotkb"


def fetch_uniprot_entry(accession: str) -> dict:
    """Fetch a UniProtKB entry as JSON. Optional connector; not used by offline demo."""
    response = requests.get(f"{BASE_URL}/{accession}.json", timeout=20)
    response.raise_for_status()
    return response.json()
