"""Public contracts. No model-produced numbers enter a forecast contract."""

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Observation(StrictModel):
    record_id: str = Field(min_length=1, max_length=100)
    dataset_id: str = Field(min_length=1, max_length=100, pattern=r"^[\w.-]+$")
    sku: str = Field(min_length=1, max_length=80, pattern=r"^[\w.-]+$")
    location: str = Field(min_length=1, max_length=80, pattern=r"^[\w.-]+$")
    date: date
    demand: float = Field(ge=0, le=1e9)
    promotion: bool = False
    stockout: bool = False
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    validation_status: Literal["valid", "warning"] = "valid"
    provenance: dict = Field(default_factory=dict)


class RunRequest(StrictModel):
    dataset_id: str = "demo-v1-seed42"
    sku: str = Field(max_length=80)
    location: str = Field(max_length=80)
    horizon: int = Field(default=14, ge=7, le=28)


class ScenarioInput(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    kind: Literal["promotion", "event", "manual"] = "manual"
    uplift_pct: float = Field(ge=-100, le=300)
    start_day: int = Field(default=1, ge=1, le=28)
    end_day: int = Field(default=14, ge=1, le=28)
    note: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def dates_in_order(self):
        if self.end_day < self.start_day:
            raise ValueError("end_day must be >= start_day")
        return self


class AIRequest(StrictModel):
    runtime: Literal["none", "ollama", "openai-local"] = "none"
    model: str = Field(default="", max_length=150)


class ParseRequest(AIRequest):
    text: str = Field(min_length=1, max_length=1000)


class EvidenceClaim(StrictModel):
    evidence_id: str
    interpretation: str = Field(min_length=1, max_length=500)


class Narrative(StrictModel):
    summary: str = Field(max_length=1200)
    claims: list[EvidenceClaim] = Field(max_length=8)
    abstained: bool
    caveats: list[str] = Field(max_length=8)


class ErrorDetail(BaseModel):
    code: str
    message: str
    trace_id: str
    details: list | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ForecastPoint(StrictModel):
    date: date
    point: float = Field(ge=0)
    lower80: float = Field(ge=0)
    upper80: float = Field(ge=0)
    lower95: float = Field(ge=0)
    upper95: float = Field(ge=0)


class RunResponse(BaseModel):
    id: str
    created_at: datetime
    dataset_id: str
    sku: str
    location: str
    horizon: int
    engine_version: str
    selected_model: str
    classification: dict
    metrics: dict[str, str | float | bool | None]
    leaderboard: list[dict]
    history: list[dict]
    forecast: list[ForecastPoint]
    forecast_total: float
    backtest: list[dict]
    origins: list[dict]
    calibration_origins: list[dict]
    evidence: list[dict]
    warnings: list[str]
    config: dict
    provenance: dict


class InventoryForecast(StrictModel):
    run_id: str
    dataset_id: str
    sku: str
    location: str
    engine_version: str
    units: Literal["units/day"] = "units/day"
    point_statistic: Literal["conditional_mean_estimate"] = "conditional_mean_estimate"
    interval_type: Literal["marginal_empirical"] = "marginal_empirical"
    forecast: list[ForecastPoint]
    warning: str
