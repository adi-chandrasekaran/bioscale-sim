from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        return


def _load_local_env_files() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    backend_root = repo_root / "backend"
    for candidate in (
        repo_root / ".env",
        repo_root / ".env.local",
        backend_root / ".env",
        backend_root / ".env.local",
    ):
        _load_env_file(candidate)


def _get_ollama_config() -> Dict[str, Any]:
    _load_local_env_files()
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    return {
        "base_url": base_url.rstrip("/"),
        "chat_url": f"{base_url.rstrip('/')}/api/chat",
        "version_url": f"{base_url.rstrip('/')}/api/version",
        "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
        "timeout_seconds": int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "40")),
    }


def _truncate_text(value: Any, limit: int = 240) -> Any:
    if not isinstance(value, str):
        return value
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _render_context(context: Dict[str, Any]) -> str:
    simulation_input = context.get("simulation_input") or {}
    disease_discovery = context.get("disease_discovery") or {}
    mutation_result = context.get("mutation_result") or {}
    protein_effect = context.get("protein_effect") or {}
    pathway_result = context.get("pathway_result") or {}
    cell_phenotype = context.get("cell_phenotype") or {}
    population_result = context.get("population_result") or {}
    ecosystem_result = context.get("ecosystem_result") or {}

    payload = {
        "simulation_input": {
            "disease_name": simulation_input.get("disease_name"),
            "gene_symbol": simulation_input.get("gene_symbol"),
            "mutation": simulation_input.get("mutation"),
            "pathway_name": simulation_input.get("pathway_name"),
        },
        "research_summary": _truncate_text(context.get("research_summary"), 260),
        "disease_discovery": {
            "label": disease_discovery.get("label"),
            "summary": _truncate_text(disease_discovery.get("summary"), 220),
            "top_candidates": [
                {
                    "symbol": candidate.get("symbol"),
                    "score": candidate.get("score"),
                    "summary": _truncate_text(candidate.get("summary"), 160),
                }
                for candidate in disease_discovery.get("candidates", [])[:4]
                if isinstance(candidate, dict)
            ],
        },
        "mutation_result": {
            "gene": mutation_result.get("gene"),
            "mutation": mutation_result.get("mutation"),
            "kind": mutation_result.get("kind"),
            "amino_acid_change": mutation_result.get("amino_acid_change"),
            "clinvar_classification": mutation_result.get("clinvar_classification"),
            "summary": _truncate_text(mutation_result.get("summary"), 220),
        },
        "protein_effect": {
            "protein_name": protein_effect.get("protein_name"),
            "protein_id": protein_effect.get("protein_id"),
            "function_summary": _truncate_text(protein_effect.get("function_summary"), 220),
            "domain_hit": protein_effect.get("domain_hit"),
            "activity": protein_effect.get("activity"),
            "stability": protein_effect.get("stability"),
            "binding": protein_effect.get("binding"),
            "loss_of_function_score": protein_effect.get("loss_of_function_score"),
        },
        "pathway_result": {
            "selected_pathway_name": pathway_result.get("selected_pathway_name"),
            "changed_nodes": (pathway_result.get("changed_nodes") or [])[:8],
            "disrupted_processes": (pathway_result.get("disrupted_processes") or [])[:8],
            "summary": _truncate_text(pathway_result.get("summary"), 240),
            "is_generic_fallback": pathway_result.get("is_generic_fallback"),
        },
        "cell_phenotype": {
            "proliferation_rate": cell_phenotype.get("proliferation_rate"),
            "apoptosis_rate": cell_phenotype.get("apoptosis_rate"),
            "repair_capacity": cell_phenotype.get("repair_capacity"),
            "genomic_instability": cell_phenotype.get("genomic_instability"),
            "stress_level": cell_phenotype.get("stress_level"),
            "inflammatory_signal": cell_phenotype.get("inflammatory_signal"),
        },
        "population_result": {
            "final_mutated_fraction": population_result.get("final_mutated_fraction"),
            "clonal_expansion_score": population_result.get("clonal_expansion_score"),
        },
        "ecosystem_result": {
            "tumor_like_burden": ecosystem_result.get("tumor_like_burden"),
            "immune_clearance": ecosystem_result.get("immune_clearance"),
            "inflammation": ecosystem_result.get("inflammation"),
            "nutrient_stress": ecosystem_result.get("nutrient_stress"),
            "ecosystem_risk_score": ecosystem_result.get("ecosystem_risk_score"),
        },
    }
    return json.dumps(payload, indent=2, default=str)


def _render_history(history: Iterable[Dict[str, str]]) -> str:
    lines: List[str] = []
    for turn in history:
        role = turn.get("role", "user")
        content = turn.get("content", "").strip()
        if content:
            lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines[-6:])


def _build_system_prompt(context: Dict[str, Any]) -> str:
    context_blob = _render_context(context)
    return (
        "You are the embedded educational biology tutor for BioScale Simulator.\n"
        "Your job is to answer the user's question using the current simulation context as the source of truth.\n"
        "Be concise, specific, and readable for a first-time learner.\n"
        "Do not repeat generic boilerplate or mention that you are a tooltip.\n"
        "If the user asks about a gene, protein, pathway node, or score, explain the exact item in the current run and how it relates to the selected disease and mutation.\n"
        "If a metric is normalized on a 0.00 to 1.00 scale, explain what that number means in this run, not a generic example.\n"
        "If the context does not contain enough information, say that plainly and suggest the most relevant panel.\n"
        "Do not invent unsupported biology.\n\n"
        f"SIMULATION CONTEXT:\n{context_blob}\n"
    )


def _build_ollama_messages(question: str, history: Iterable[Dict[str, str]], context: Dict[str, Any]) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = [{"role": "system", "content": _build_system_prompt(context)}]
    for turn in history:
        role = turn.get("role", "user")
        content = turn.get("content", "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question.strip()})
    return messages


def _ollama_available() -> bool:
    config = _get_ollama_config()
    try:
        with urllib.request.urlopen(config["version_url"], timeout=3) as response:
            _ = response.read()
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def ai_status() -> Dict[str, str | bool | None]:
    config = _get_ollama_config()
    if _ollama_available():
        return {
            "configured": True,
            "provider": "ollama",
            "model": config["model"],
            "message": f"Connected to local Ollama ({config['model']}) at {config['base_url']}.",
        }
    return {
        "configured": False,
        "provider": "unavailable",
        "model": None,
        "message": "No local LLM is running. Start Ollama and pull the configured model.",
    }


def _ollama_answer(question: str, history: Iterable[Dict[str, str]], context: Dict[str, Any]) -> str:
    config = _get_ollama_config()
    prompt_payload = {
        "model": config["model"],
        "messages": _build_ollama_messages(question, history, context),
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
        "keep_alive": "5m",
    }
    body = json.dumps(prompt_payload).encode("utf-8")
    request = urllib.request.Request(
        config["chat_url"],
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=config["timeout_seconds"]) as response:
        payload = json.loads(response.read().decode("utf-8"))
    message = payload.get("message") or {}
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    return "I could not extract a response from the local LLM service."


def answer_question(question: str, history: Iterable[Dict[str, str]], context: Dict[str, Any]) -> Dict[str, str]:
    if not _ollama_available():
        raise RuntimeError(
            "No local LLM backend is configured. Start Ollama and pull the configured model."
        )

    try:
        config = _get_ollama_config()
        return {
            "answer": _ollama_answer(question, history, context),
            "provider": "ollama",
            "model": config["model"],
        }
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"The local LLM could not be reached: {exc}") from exc
