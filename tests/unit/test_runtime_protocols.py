import httpx
import pytest
from demandsense.ai import HTTPRuntime, discover, parse_scenario
from demandsense.schemas import ParseRequest
from demandsense.storage import telemetry


def mock_client(monkeypatch, handler):
    original = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=transport, **kwargs))


def test_ollama_discovery_excludes_cloud_and_validates_installed_model(monkeypatch):
    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": "local:8b", "digest": "sha"}, {"name": "remote:cloud"}]}
            )
        if request.url.path == "/api/show":
            return httpx.Response(200, json={})
        if request.url.path == "/api/chat":
            return httpx.Response(200, json={"message": {"content": '{"ok": true}'}, "eval_count": 5})
        return httpx.Response(404)

    mock_client(monkeypatch, handler)
    runtime = HTTPRuntime("ollama")
    assert [m["id"] for m in runtime.models()] == ["local:8b"]
    raw, usage = runtime.complete("local:8b", {}, "test", {})
    assert raw == '{"ok": true}' and usage["output_tokens"] == 5
    with pytest.raises(ValueError, match="installed"):
        runtime.complete("not-installed", {}, "test", {})


def test_cloud_backed_tag_is_rejected_even_without_cloud_name(monkeypatch):
    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "innocent-name"}]})
        return httpx.Response(200, json={"remote_host": "https://remote.example"})

    mock_client(monkeypatch, handler)
    with pytest.raises(ValueError, match="Cloud-backed"):
        HTTPRuntime("ollama").complete("innocent-name", {}, "test", {})


def test_local_openai_compatible_adapter(monkeypatch):
    def handler(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "local-gguf"}]})
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "{}"}}], "usage": {"total_tokens": 10}}
        )

    mock_client(monkeypatch, handler)
    raw, usage = HTTPRuntime("openai-local").complete("local-gguf", {}, "test", {})
    assert raw == "{}" and usage["usage"]["total_tokens"] == 10


def test_discovery_when_runtimes_offline(monkeypatch):
    mock_client(monkeypatch, lambda request: httpx.Response(503))
    assert all(r["status"] == "unavailable" for r in discover()["runtimes"])


def test_scenario_draft_does_not_apply_and_rejects_missing_numbers(monkeypatch, repo):
    payload = '{"name":"Promo","uplift_pct":25,"start_day":1,"end_day":7}'
    monkeypatch.setattr(HTTPRuntime, "complete", lambda *args: (payload, {}))
    draft = parse_scenario(
        repo, ParseRequest(runtime="ollama", model="test", text="25% from day 1 through 7")
    )
    assert draft["requires_review"] and draft["draft"]["uplift_pct"] == 25
    payload = '{"name":"Promo","uplift_pct":25}'
    with pytest.raises(ValueError, match="valid scenario"):
        parse_scenario(repo, ParseRequest(runtime="ollama", model="test", text="Do something"))
    assert repo.recent(telemetry)[0]["status"] == "rejected"
    with pytest.raises(ValueError, match="Select an installed"):
        parse_scenario(repo, ParseRequest(text="hello"))
