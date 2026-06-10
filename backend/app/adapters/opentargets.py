from __future__ import annotations

import requests

BASE_URL = "https://api.platform.opentargets.org/api/v4/graphql"


def graphql_query(query: str, variables: dict | None = None) -> dict:
    """Run an Open Targets GraphQL query. Optional connector; not used by offline demo."""
    response = requests.post(BASE_URL, json={"query": query, "variables": variables or {}}, timeout=30)
    response.raise_for_status()
    return response.json()
