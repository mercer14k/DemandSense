import csv
import io

from demandsense.generator import generate
from demandsense.storage import observations
from sqlalchemy import func, select


def run_payload():
    return {"sku": "SKU-0001", "location": "CHI"}


def csv_bytes(rows):
    f = io.StringIO()
    columns = ["record_id", "dataset_id", "sku", "location", "date", "demand", "promotion", "stockout"]
    writer = csv.DictWriter(f, columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return f.getvalue().encode()


def test_end_to_end_forecast_scenario_export_evidence(client, headers):
    assert client.get("/health").status_code == 200
    assert client.get("/ready").json()["status"] == "ready"
    catalog = client.get("/api/v1/series?limit=2").json()
    assert catalog["total"] == 15 and len(catalog["items"]) == 2
    response = client.post("/api/v1/runs", json=run_payload(), headers=headers)
    assert response.status_code == 201, response.text
    run = response.json()
    assert len(run["forecast"]) == 14
    assert response.headers["X-Trace-ID"]
    repeat = client.post("/api/v1/runs", json=run_payload(), headers=headers)
    assert repeat.json() == run
    sid = client.post(
        f"/api/v1/runs/{run['id']}/scenarios",
        json={"name": "Promotion", "uplift_pct": 20},
        headers={**headers, "Idempotency-Key": "scenario-operation-001"},
    ).json()
    assert sid["scenario_total"] > sid["baseline_total"]
    assert client.get(f"/api/v1/runs/{run['id']}").json() == run
    evidence = client.post(
        f"/api/v1/runs/{run['id']}/explanations", json={"runtime": "none"}, headers=headers
    ).json()
    assert evidence["mode"] == "deterministic" and evidence["narrative"]["claims"]
    inventory = client.get(f"/api/v1/inventory/forecasts/{run['id']}").json()
    assert inventory["interval_type"] == "marginal_empirical"
    assert len(client.get(f"/api/v1/runs/{run['id']}/export").text.splitlines()) == 15


def test_missing_or_invalid_authorization(client):
    for headers in ({}, {"X-DemandSense-Token": "wrong"}):
        assert client.post("/api/v1/runs", json=run_payload(), headers=headers).status_code == 403


def test_idempotency_conflict_and_unknown_fields(client, headers):
    assert client.post("/api/v1/runs", json=run_payload(), headers=headers).status_code == 201
    res = client.post("/api/v1/runs", json={**run_payload(), "horizon": 7}, headers=headers)
    assert res.status_code == 422
    assert "different input" in res.json()["error"]["message"]
    assert (
        client.post(
            "/api/v1/runs", json={**run_payload(), "arbitrary_sql": "DROP TABLE"}, headers=headers
        ).status_code
        == 422
    )


def test_errors_are_consistent(client, headers):
    assert client.get("/api/v1/runs/not-found").status_code == 404
    assert client.get("/api/v1/series?limit=9999").status_code == 422
    response = client.post("/api/v1/runs", json={"sku": "missing", "location": "CHI"}, headers=headers)
    assert response.status_code == 404
    assert {"code", "message", "trace_id", "details"} == set(response.json()["error"])


def test_atomic_import_validation_report(client, headers, repo):
    rows = list(generate(1, 196))
    for r in rows:
        r["dataset_id"] = "import-v1"
        r["record_id"] = "import-" + r["record_id"]
    bad = [dict(r) for r in rows]
    bad[10]["demand"] = -1
    result = client.post(
        "/api/v1/imports", headers=headers, files={"file": ("../../bad.csv", csv_bytes(bad), "text/csv")}
    ).json()
    assert result["status"] == "rejected" and result["accepted"] == 0
    assert result["filename"] == "bad.csv"
    assert any(i["line"] == 12 for i in result["issues"])
    with repo.engine.connect() as conn:
        assert (
            conn.execute(
                select(func.count()).select_from(observations).where(observations.c.dataset_id == "import-v1")
            ).scalar_one()
            == 0
        )
    good = client.post(
        "/api/v1/imports",
        headers={**headers, "Idempotency-Key": "valid-import-001"},
        files={"file": ("good.csv", csv_bytes(rows), "text/csv")},
    ).json()
    assert good["accepted"] == 588
    new_run = client.post(
        "/api/v1/runs",
        json={**run_payload(), "dataset_id": "import-v1"},
        headers={**headers, "Idempotency-Key": "imported-run-001"},
    )
    assert new_run.status_code == 201
    assert len(client.get("/api/v1/validation-reports").json()["items"]) == 3


def test_upload_mime_size_duplicate_and_encoding(client, headers):
    assert (
        client.post(
            "/api/v1/imports", headers=headers, files={"file": ("x.html", b"hello", "text/html")}
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/api/v1/imports",
            headers=headers,
            files={"file": ("x.csv", b"a" * (10 * 1024 * 1024 + 1), "text/csv")},
        ).status_code
        == 413
    )
    bad = client.post(
        "/api/v1/imports", headers=headers, files={"file": ("x.csv", b"\xff\xff", "text/csv")}
    ).json()
    assert bad["status"] == "rejected"
    rows = list(generate(1, 28))
    result = client.post(
        "/api/v1/imports",
        headers={**headers, "Idempotency-Key": "duplicate-001"},
        files={"file": ("x.csv", csv_bytes(rows + rows[:1]), "text/csv")},
    ).json()
    assert result["status"] == "rejected" and any("Duplicate" in x["message"] for x in result["issues"])


def test_sql_injection_search_is_data(client):
    assert client.get("/api/v1/series", params={"q": "'; DROP TABLE observations;--"}).json()["items"] == []
    assert client.get("/api/v1/series").json()["total"] == 15


def test_private_mode_read_only_boundary(repo, monkeypatch):
    from fastapi.testclient import TestClient

    from apps.api.main import create_app

    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("WRITE_TOKEN", "private-write-test-token")
    monkeypatch.setenv("READ_TOKEN", "private-read-test-token")
    with TestClient(create_app(repo, seed_demo=False)) as client:
        assert client.get("/api/v1/datasets").status_code == 401
        read = {"X-DemandSense-Token": "private-read-test-token"}
        assert client.get("/api/v1/datasets", headers=read).status_code == 200
        assert client.get("/api/v1/config", headers=read).json()["write_token"] is None
        assert client.post("/api/v1/runs", headers=read, json=run_payload()).status_code == 403


def test_chunked_request_body_limit(client, headers):
    def chunks():
        for _ in range(12):
            yield b"a" * 1024 * 1024

    response = client.post(
        "/api/v1/runs", content=chunks(), headers={**headers, "content-type": "application/json"}
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
