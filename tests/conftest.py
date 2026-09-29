import pytest
from demandsense.generator import generate
from demandsense.storage import Repository
from fastapi.testclient import TestClient

from apps.api.main import create_app


@pytest.fixture
def series():
    return [r for r in generate(1, 196, 42) if r["location"] == "CHI"]


@pytest.fixture
def repo():
    repository = Repository("sqlite:///:memory:")
    repository.initialize()
    yield repository
    repository.engine.dispose()


@pytest.fixture
def client(repo, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("WRITE_TOKEN", "test-write-token")
    repo.seed(skus=5, days=196)
    with TestClient(create_app(repo, seed_demo=False)) as client:
        yield client


@pytest.fixture
def headers():
    return {"X-DemandSense-Token": "test-write-token", "Idempotency-Key": "test-operation-001"}
