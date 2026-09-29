import hashlib
import json

from demandsense.forecasting import VERSION, analyze, apply_scenario
from demandsense.storage import now, runs, scenarios


class ForecastService:
    def __init__(self, repo):
        self.repo = repo

    def create_run(self, request):
        identity = {**request.model_dump(), "engine": VERSION}
        run_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]
        with self.repo.lock:
            cached = self.repo.get(runs, run_id)
            if cached:
                return cached
            rows = self.repo.series(request.dataset_id, request.sku, request.location)
            if not rows:
                raise LookupError("No observations for this SKU/location/dataset")
            result = analyze(rows, request.horizon)
            result.update(id=run_id, created_at=now(), **request.model_dump())
            result["provenance"] = {
                "dataset_id": request.dataset_id,
                "source_record_count": len(rows),
                "first_source_id": rows[0]["record_id"],
                "last_source_id": rows[-1]["record_id"],
                "source_ids_sha256": hashlib.sha256(
                    "|".join(r["record_id"] for r in rows).encode()
                ).hexdigest(),
            }
            self.repo.save(runs, run_id, result)
            return result

    def scenario(self, run_id, inputs):
        run = self.repo.get(runs, run_id)
        if run is None:
            raise LookupError("Forecast run not found")
        sid = hashlib.sha256((run_id + inputs.model_dump_json()).encode()).hexdigest()[:24]
        with self.repo.lock:
            cached = self.repo.get(scenarios, sid)
            if cached:
                return cached
            result = {"id": sid, "run_id": run_id, "created_at": now(), **apply_scenario(run, inputs)}
            self.repo.save(scenarios, sid, result, run_id=run_id)
            return result
