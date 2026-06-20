from __future__ import annotations

import json

import pytest

from app.services import ai_assistant
from app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_answer_question_requires_local_llm(monkeypatch):
    monkeypatch.setattr(ai_assistant, "_load_local_env_files", lambda: None)
    monkeypatch.setattr(ai_assistant, "_ollama_available", lambda: False)

    with pytest.raises(RuntimeError, match="No local LLM backend is configured"):
        ai_assistant.answer_question("What does TP53 do?", [], {})


def test_answer_question_parses_ollama_response(monkeypatch):
    monkeypatch.setattr(ai_assistant, "_load_local_env_files", lambda: None)
    monkeypatch.setattr(ai_assistant, "_ollama_available", lambda: True)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"message": {"content": "TP53 is a tumor suppressor that helps control DNA damage responses."}}).encode("utf-8")

    def fake_urlopen(request, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        assert timeout == 40
        assert payload["model"] == "llama3.2"
        assert payload["messages"][0]["role"] == "system"
        assert "SIMULATION CONTEXT" in payload["messages"][0]["content"]
        return FakeResponse()

    monkeypatch.setattr(ai_assistant.urllib.request, "urlopen", fake_urlopen)

    result = ai_assistant.answer_question("What does TP53 do?", [], {"research_summary": "Selected cancer, gene TP53."})

    assert result["provider"] == "ollama"
    assert result["model"] == "llama3.2"
    assert "tumor suppressor" in result["answer"]


def test_ai_status_endpoint_reports_configuration(monkeypatch):
    monkeypatch.setattr(ai_assistant, "_load_local_env_files", lambda: None)
    monkeypatch.setattr(ai_assistant, "_ollama_available", lambda: False)
    response = client.get("/api/ai/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is False
    assert payload["provider"] == "unavailable"
