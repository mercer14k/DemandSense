"""SQLAlchemy repository; PostgreSQL in Compose, SQLite for native first run."""

import csv
import hashlib
import io
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    func,
    insert,
    select,
)

from demandsense.generator import generate
from demandsense.schemas import Observation

metadata = MetaData()
datasets = Table(
    "datasets",
    metadata,
    Column("id", String(100), primary_key=True),
    Column("created_at", String),
    Column("source", String),
    Column("record_count", Integer),
    Column("sha256", String),
    Column("provenance", JSON),
)
observations = Table(
    "observations",
    metadata,
    Column("record_id", String(100), primary_key=True),
    Column("dataset_id", String(100), nullable=False),
    Column("sku", String(80)),
    Column("location", String(80)),
    Column("date", String(10)),
    Column("demand", Float),
    Column("promotion", Boolean),
    Column("stockout", Boolean),
    Column("ingested_at", String),
    Column("validation_status", String),
    Column("provenance", JSON),
)
Index(
    "series_day",
    observations.c.dataset_id,
    observations.c.sku,
    observations.c.location,
    observations.c.date,
    unique=True,
)
reports = Table(
    "validation_reports",
    metadata,
    Column("id", String, primary_key=True),
    Column("created_at", String),
    Column("payload", JSON),
)
runs = Table(
    "forecast_runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("created_at", String),
    Column("payload", JSON),
)
scenarios = Table(
    "scenarios",
    metadata,
    Column("id", String, primary_key=True),
    Column("run_id", String),
    Column("created_at", String),
    Column("payload", JSON),
)
requests = Table(
    "idempotency",
    metadata,
    Column("id", String, primary_key=True),
    Column("fingerprint", String),
    Column("payload", JSON),
)
telemetry = Table(
    "ai_telemetry",
    metadata,
    Column("id", String, primary_key=True),
    Column("created_at", String),
    Column("payload", JSON),
)


def now():
    return datetime.now(timezone.utc).isoformat()


class Repository:
    def __init__(self, url=None):
        url = url or os.getenv("DATABASE_URL", "sqlite:///./var/demandsense.db")
        if url.startswith("sqlite") and ":memory:" not in url:
            Path("var").mkdir(exist_ok=True)
        opts = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
        if ":memory:" in url:
            from sqlalchemy.pool import StaticPool

            opts["poolclass"] = StaticPool
        self.engine = create_engine(url, pool_pre_ping=True, **opts)
        read_url = os.getenv("DATABASE_READ_URL")
        self.read_engine = create_engine(read_url, pool_pre_ping=True) if read_url else self.engine
        self.lock = threading.RLock()

    def initialize(self):
        metadata.create_all(self.engine)

    def seed(self, skus=500, days=196, seed=42):
        did = f"demo-v1-seed{seed}"
        with self.lock, self.engine.begin() as conn:
            if conn.execute(select(datasets.c.id).where(datasets.c.id == did)).first():
                return
            count, batch = 0, []
            digest = hashlib.sha256()
            stamp = now()
            for row in generate(skus, days, seed):
                digest.update(json.dumps(row, sort_keys=True).encode())
                row["ingested_at"] = stamp
                batch.append(row)
                if len(batch) == 3000:
                    conn.execute(insert(observations), batch)
                    count += len(batch)
                    batch = []
            if batch:
                conn.execute(insert(observations), batch)
                count += len(batch)
            conn.execute(
                insert(datasets).values(
                    id=did,
                    created_at=stamp,
                    source="seeded synthetic generator",
                    record_count=count,
                    sha256=digest.hexdigest(),
                    provenance={
                        "seed": seed,
                        "skus": skus,
                        "days": days,
                        "locations": 3,
                        "generator": "synthetic-1.0",
                    },
                )
            )
            warning_count = conn.execute(
                select(func.count())
                .select_from(observations)
                .where(observations.c.dataset_id == did, observations.c.stockout)
            ).scalar_one()
            payload = {
                "id": f"seed-{did}",
                "dataset_id": did,
                "status": "accepted",
                "rows": count,
                "accepted": count,
                "rejected": 0,
                "warnings": warning_count,
                "issues": [],
                "note": "Known synthetic stockout flags retained as warnings; latent ground truth excluded from model features.",
            }
            conn.execute(insert(reports).values(id=payload["id"], created_at=stamp, payload=payload))

    def dataset_list(self):
        with self.read_engine.connect() as conn:
            return [dict(r) for r in conn.execute(select(datasets)).mappings()]

    def catalog(self, dataset_id, q="", location="", offset=0, limit=50):
        o = observations.c
        query = select(
            o.sku,
            o.location,
            func.count().label("days"),
            func.sum(o.demand).label("units"),
            func.avg(o.demand).label("daily_mean"),
            func.min(o.date).label("start"),
            func.max(o.date).label("end"),
            func.sum(o.promotion.cast(Integer)).label("promo_days"),
            func.sum(o.stockout.cast(Integer)).label("stockout_days"),
        )
        query = query.where(o.dataset_id == dataset_id)
        if q:
            query = query.where(o.sku.ilike("%" + q.replace("%", "").replace("_", "") + "%"))
        if location:
            query = query.where(o.location == location)
        grouped = query.group_by(o.sku, o.location)
        with self.read_engine.connect() as conn:
            total = conn.execute(select(func.count()).select_from(grouped.subquery())).scalar_one()
            rows = [
                dict(r)
                for r in conn.execute(
                    grouped.order_by(o.sku, o.location).offset(offset).limit(limit)
                ).mappings()
            ]
        return {"items": rows, "total": total, "offset": offset, "limit": limit}

    def series(self, dataset_id, sku, location):
        with self.read_engine.connect() as conn:
            return [
                dict(r)
                for r in conn.execute(
                    select(observations)
                    .where(
                        observations.c.dataset_id == dataset_id,
                        observations.c.sku == sku,
                        observations.c.location == location,
                    )
                    .order_by(observations.c.date)
                ).mappings()
            ]

    def get(self, table, key):
        with self.read_engine.connect() as conn:
            row = conn.execute(select(table.c.payload).where(table.c.id == key)).first()
            return row[0] if row else None

    def save(self, table, key, payload, **extra):
        with self.engine.begin() as conn:
            conn.execute(insert(table).values(id=key, created_at=now(), payload=payload, **extra))

    def recent(self, table, limit=30, offset=0):
        with self.read_engine.connect() as conn:
            return list(
                conn.execute(
                    select(table.c.payload).order_by(table.c.created_at.desc()).offset(offset).limit(limit)
                ).scalars()
            )

    def idempotent(self, key, fingerprint, action):
        with self.lock:
            with self.engine.connect() as conn:
                row = conn.execute(select(requests).where(requests.c.id == key)).mappings().first()
            if row:
                if row["fingerprint"] != fingerprint:
                    raise ValueError("Idempotency key was already used with different input")
                return row["payload"]
            payload = action()
            with self.engine.begin() as conn:
                conn.execute(insert(requests).values(id=key, fingerprint=fingerprint, payload=payload))
            return payload

    def ingest_csv(self, content, filename):
        report_id = str(uuid4())
        report = {
            "id": report_id,
            "filename": Path(filename.replace("\\", "/")).name[:100],
            "status": "rejected",
            "rows": 0,
            "accepted": 0,
            "rejected": 0,
            "warnings": 0,
            "issues": [],
        }
        valid, keys, ids, dataset_ids = [], set(), set(), set()
        try:
            text = content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            if not reader.fieldnames or not {
                "record_id",
                "dataset_id",
                "sku",
                "location",
                "date",
                "demand",
            }.issubset(reader.fieldnames):
                raise ValueError("Missing required CSV columns; see data dictionary")
            if len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError("Duplicate CSV column names")
            for line, row in enumerate(reader, 2):
                report["rows"] += 1
                if report["rows"] > 250_000:
                    raise ValueError("Maximum 250000 records per upload")
                try:
                    if row.get("provenance"):
                        row["provenance"] = json.loads(row["provenance"])
                    else:
                        row.pop("provenance", None)
                    row["ingested_at"] = now()
                    obs = Observation.model_validate(row)
                    key = (obs.dataset_id, obs.sku, obs.location, obs.date)
                    if key in keys or obs.record_id in ids:
                        raise ValueError("Duplicate record_id or SKU/location/date")
                    keys.add(key)
                    ids.add(obs.record_id)
                    dataset_ids.add(obs.dataset_id)
                    if obs.stockout:
                        obs.validation_status = "warning"
                        report["warnings"] += 1
                    valid.append(obs.model_dump(mode="json"))
                except (ValidationError, ValueError, TypeError) as exc:
                    report["issues"].append(
                        {"line": line, "code": "invalid_record", "message": str(exc)[:500]}
                    )
            if not valid and not report["issues"]:
                raise ValueError("CSV contains no data rows")
            if len(dataset_ids) != 1:
                raise ValueError("Each upload must contain exactly one dataset_id")
            if report["issues"]:
                raise ValueError("Atomic import rejected; correct every reported issue and retry")
            dataset_id = next(iter(dataset_ids))
            with self.lock, self.engine.begin() as conn:
                if conn.execute(select(datasets.c.id).where(datasets.c.id == dataset_id)).first():
                    raise ValueError(
                        "Dataset already exists; import a new version with new record identifiers"
                    )
                for i in range(0, len(valid), 3000):
                    conn.execute(insert(observations), valid[i : i + 3000])
                conn.execute(
                    insert(datasets).values(
                        id=dataset_id,
                        created_at=now(),
                        source=report["filename"],
                        record_count=len(valid),
                        sha256=hashlib.sha256(content).hexdigest(),
                        provenance={"import_report": report_id},
                    )
                )
            report.update(status="accepted", accepted=len(valid), dataset_id=dataset_id)
        except (UnicodeDecodeError, ValueError, csv.Error) as exc:
            report["issues"].append({"line": None, "code": "invalid_dataset", "message": str(exc)[:500]})
        except Exception:
            report["issues"].append(
                {
                    "line": None,
                    "code": "storage_conflict",
                    "message": "Import rolled back: record identifiers conflict or storage unavailable.",
                }
            )
        report["rejected"] = report["rows"] - report["accepted"]
        self.save(reports, report_id, report)
        return report
