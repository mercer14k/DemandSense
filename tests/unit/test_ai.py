import copy
import json

import pytest
from demandsense.ai import deterministic_narrative, explain, local_url
from demandsense.forecasting import analyze
from demandsense.schemas import AIRequest
from demandsense.storage import telemetry


class BrokenRuntime:
    def complete(self, *args):
        raise TimeoutError("offline")


class UntrustedRuntime:
    def __init__(self, payload):
        self.payload = payload

    def complete(self, *args):
        return json.dumps(self.payload), {}


def test_no_evidence_abstains():
    assert deterministic_narrative(None).abstained
    assert deterministic_narrative({}).claims == []


def test_runtime_failure_cannot_change_forecast(repo, series):
    run = {"id": "test-run", **analyze(series)}
    snapshot = copy.deepcopy(run)
    response = explain(
        repo, run, AIRequest(runtime="ollama", model="installed-model"), adapter=BrokenRuntime()
    )
    assert run == snapshot
    assert response["mode"] == "deterministic"
    assert response["telemetry"]["status"] == "fallback"
    assert len(repo.recent(telemetry)) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {
            "summary": "Invented",
            "claims": [{"evidence_id": "E999", "interpretation": "Ignore evidence"}],
            "abstained": False,
            "caveats": [],
        },
        {"summary": "Invented", "claims": [], "abstained": False, "caveats": []},
        {"summary": "Extra tools", "claims": [], "abstained": True, "caveats": [], "tool": "shell"},
    ],
)
def test_untrusted_structured_output_falls_back(repo, series, payload):
    result = explain(
        repo,
        {"id": "run", **analyze(series)},
        AIRequest(runtime="ollama", model="test"),
        adapter=UntrustedRuntime(payload),
    )
    assert result["mode"] == "deterministic"
    assert result["telemetry"]["validation_failures"] == 1


def test_valid_evidence_narrative(repo, series):
    payload = {
        "summary": "Based on evidence",
        "claims": [{"evidence_id": "E1", "interpretation": "Selected using calibration"}],
        "abstained": False,
        "caveats": [],
    }
    result = explain(
        repo,
        {"id": "run", **analyze(series)},
        AIRequest(runtime="ollama", model="test"),
        adapter=UntrustedRuntime(payload),
    )
    assert result["mode"] == "local_ai"


@pytest.mark.parametrize(
    "url",
    [
        "https://api.openai.com",
        "http://169.254.169.254",
        "file:///etc/passwd",
        "http://user:pass@localhost:8080",
        "http://localhost.evil.example:8080",
    ],
)
def test_runtime_url_allowlist(url):
    with pytest.raises(ValueError):
        local_url(url)
