from __future__ import annotations

import requests

BASE_URL = "https://string-db.org/api/json"


def fetch_interactions(gene_symbol: str, species: int = 9606, limit: int = 10) -> list[dict]:
    """Fetch STRING interaction partners. Optional connector; not used by offline demo."""
    response = requests.get(
        f"{BASE_URL}/network",
        params={"identifiers": gene_symbol, "species": species, "limit": limit},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
