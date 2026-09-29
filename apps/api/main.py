import csv
import hashlib
import io
import json
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from demandsense.ai import discover, explain, parse_scenario
from demandsense.http_security import BodyLimitMiddleware
from demandsense.schemas import (
    AIRequest,
    ErrorResponse,
    InventoryForecast,
    ParseRequest,
    RunRequest,
    RunResponse,
    ScenarioInput,
)
from demandsense.services import ForecastService
from demandsense.storage import Repository, reports, runs, scenarios, telemetry
from fastapi import APIRouter, Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("demandsense")


def create_app(repo=None, seed_demo=True):
    repository = repo or Repository()
    service = ForecastService(repository)
    demo = os.getenv("DEMO_MODE", "true").lower() == "true"
    write_token = os.getenv("WRITE_TOKEN", "local-demo-change-me" if demo else "")
    read_token = os.getenv("READ_TOKEN", "")
    if not write_token or (not demo and write_token == "local-demo-change-me"):
        raise RuntimeError("Set a unique WRITE_TOKEN when DEMO_MODE=false")

    @asynccontextmanager
    async def lifespan(app):
        repository.initialize()
        if seed_demo and demo:
            repository.seed(
                int(os.getenv("DEMO_SKUS", "500")),
                int(os.getenv("DEMO_DAYS", "196")),
                int(os.getenv("SEED", "42")),
            )
        yield
        repository.engine.dispose()

    app = FastAPI(
        title="DemandSense API",
        version="1.0.0",
        lifespan=lifespan,
        description="Deterministic forecasts, empirical intervals, and evidence-backed local AI.",
        docs_url="/docs" if demo else None,
        redoc_url="/redoc" if demo else None,
        openapi_url="/openapi.json" if demo else None,
    )
    app.state.repo = repository
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver,api").split(","),
    )

    @app.middleware("http")
    async def trace(request, call_next):
        request.state.trace_id = str(uuid4())
        start = time.perf_counter()
        response = await call_next(request)
        if response.status_code >= 400 and "application/json" not in response.headers.get("content-type", ""):
            response = error(request, response.status_code, "http_error", "Request rejected by HTTP boundary")
        response.headers.update(
            {
                "X-Trace-ID": request.state.trace_id,
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "same-origin",
                "Cache-Control": "no-store",
            }
        )
        logger.info(
            json.dumps(
                {
                    "trace_id": request.state.trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                }
            )
        )
        return response

    def error(request, status, code, message, details=None):
        return JSONResponse(
            status_code=status,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "trace_id": getattr(request.state, "trace_id", "unknown"),
                    "details": details,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return error(request, exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return error(
            request,
            422,
            "validation_error",
            "Request validation failed",
            [{"field": ".".join(str(x) for x in e["loc"]), "message": e["msg"]} for e in exc.errors()],
        )

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        return error(request, 422, "invalid_operation", str(exc))

    @app.exception_handler(LookupError)
    async def missing(request, exc):
        return error(request, 404, "not_found", str(exc))

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        logger.error(
            json.dumps(
                {"trace_id": getattr(request.state, "trace_id", "unknown"), "error_type": type(exc).__name__}
            )
        )
        return error(
            request, 500, "internal_error", "Request failed; inspect the server log using the trace ID"
        )

    def authorize_read(x_demandsense_token: str = Header(default="")):
        if not demo and not any(
            t and secrets.compare_digest(x_demandsense_token, t) for t in (write_token, read_token)
        ):
            raise HTTPException(401, "Read credential required")

    def authorize_write(x_demandsense_token: str = Header(default="")):
        if not secrets.compare_digest(x_demandsense_token, write_token):
            raise HTTPException(403, "Valid write credential required")

    def mutate(key, payload, fn):
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return repository.idempotent(key, fingerprint, fn)

    def required_run(run_id):
        result = repository.get(runs, run_id)
        if not result:
            raise LookupError("Forecast run not found")
        return result

    @app.get("/health", tags=["Operations"])
    def health():
        return {"status": "healthy", "version": "0.1.0"}

    @app.get("/ready", tags=["Operations"])
    def ready():
        try:
            with repository.read_engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception:
            raise HTTPException(503, "Database unavailable") from None

    read = APIRouter(
        prefix="/api/v1",
        dependencies=[Depends(authorize_read)],
        tags=["Read"],
        responses={422: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    write = APIRouter(
        prefix="/api/v1",
        dependencies=[Depends(authorize_write)],
        tags=["Mutations"],
        responses={403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )

    @read.get("/config")
    def config():
        return {"demo_mode": demo, "write_token": write_token if demo else None, "default_runtime": "none"}

    @read.get("/datasets")
    def get_datasets():
        return {"items": repository.dataset_list()}

    @read.get("/series")
    def series(
        dataset_id: str = "demo-v1-seed42",
        q: str = Query("", max_length=80),
        location: str = "",
        offset: int = Query(0, ge=0),
        limit: int = Query(30, ge=1, le=200),
    ):
        return repository.catalog(dataset_id, q, location, offset, limit)

    @read.get("/runs")
    def list_runs(limit: int = Query(30, ge=1, le=200), offset: int = Query(0, ge=0)):
        return {"items": repository.recent(runs, limit, offset)}

    @read.get("/runs/{run_id}", response_model=RunResponse)
    def get_run(run_id: str):
        return required_run(run_id)

    @write.post("/runs", response_model=RunResponse, status_code=201)
    def create_run(inputs: RunRequest, idempotency_key: str = Header(min_length=8, max_length=128)):
        return mutate(
            idempotency_key, {"action": "run", **inputs.model_dump()}, lambda: service.create_run(inputs)
        )

    @write.post("/runs/{run_id}/scenarios", status_code=201)
    def scenario(
        run_id: str, inputs: ScenarioInput, idempotency_key: str = Header(min_length=8, max_length=128)
    ):
        return mutate(
            idempotency_key,
            {"action": "scenario", "run_id": run_id, **inputs.model_dump()},
            lambda: service.scenario(run_id, inputs),
        )

    @read.get("/scenarios/{scenario_id}")
    def get_scenario(scenario_id: str):
        result = repository.get(scenarios, scenario_id)
        if result is None:
            raise LookupError("Scenario not found")
        return result

    @read.get("/inventory/forecasts/{run_id}", response_model=InventoryForecast)
    def inventory(run_id: str):
        result = required_run(run_id)
        return {
            "run_id": run_id,
            **{k: result[k] for k in ("dataset_id", "sku", "location", "engine_version", "forecast")},
            "warning": "Do not sum daily interval bounds into a lead-time service quantile. Cross-day dependence is not modeled.",
        }

    @read.get("/runs/{run_id}/export")
    def export(run_id: str):
        result = required_run(run_id)
        output = io.StringIO()
        writer = csv.DictWriter(
            output, fieldnames=["date", "point", "lower80", "upper80", "lower95", "upper95"]
        )
        writer.writeheader()
        writer.writerows(result["forecast"])
        return Response(
            output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="forecast-{result["id"]}.csv"'},
        )

    @write.post("/imports", status_code=201)
    async def upload(file: UploadFile = File(), idempotency_key: str = Header(min_length=8, max_length=128)):
        if file.content_type not in {"text/csv", "text/plain", "application/vnd.ms-excel"} or not (
            file.filename or ""
        ).lower().endswith(".csv"):
            raise HTTPException(415, "Upload a UTF-8 .csv file with a CSV/text MIME type")
        content = await file.read(10 * 1024 * 1024 + 1)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, "CSV maximum size is 10 MiB")
        return await run_in_threadpool(
            mutate,
            idempotency_key,
            {"action": "import", "sha256": hashlib.sha256(content).hexdigest()},
            lambda: repository.ingest_csv(content, file.filename),
        )

    @read.get("/validation-reports")
    def validation_reports(limit: int = Query(30, ge=1, le=200), offset: int = Query(0, ge=0)):
        return {"items": repository.recent(reports, limit, offset)}

    @read.get("/models")
    def models():
        return discover()

    @write.post("/runs/{run_id}/explanations")
    def explanation(run_id: str, inputs: AIRequest, request: Request):
        return explain(repository, required_run(run_id), inputs, trace_id=request.state.trace_id)

    @write.post("/scenario-drafts")
    def draft(inputs: ParseRequest, request: Request):
        return parse_scenario(repository, inputs, request.state.trace_id)

    @read.get("/telemetry")
    def events(limit: int = Query(30, ge=1, le=200), offset: int = Query(0, ge=0)):
        return {"items": repository.recent(telemetry, limit, offset)}

    app.add_middleware(BodyLimitMiddleware)
    app.include_router(read)
    app.include_router(write)
    return app


app = create_app()
