import { useState } from "react";
import {
  ArrowDownToLine,
  ArrowUpRight,
  FlaskConical,
  Info,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { api, num, pct, title } from "./api";
import { ForecastChart } from "./Chart";
import type {
  Dataset,
  Model,
  Report,
  Run,
  Scenario,
  ScenarioInput,
} from "./types";

export function Leaderboard({ run }: { run: Run }) {
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">MODEL COMPARISON</span>
          <h2>Let the evidence choose.</h2>
        </div>
        <span className="muted small">Ranked by pre-test MAE</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>Selection MAE</th>
              <th>Test WAPE</th>
              <th>MASE</th>
              <th>RMSE</th>
              <th>Bias</th>
              <th>80% coverage</th>
            </tr>
          </thead>
          <tbody>
            {run.leaderboard.map((s, i) => (
              <tr key={s.model} className={s.selected ? "chosen" : ""}>
                <td>
                  <span className="rank">0{i + 1}</span>
                  {title(s.model)}
                  {s.selected && <span className="tag mint">Selected</span>}
                </td>
                <td>{num(s.selection_mae, 2)}</td>
                <td>{pct(s.wape)}</td>
                <td>{num(s.mase, 2)}</td>
                <td>{num(s.rmse, 2)}</td>
                <td
                  className={
                    s.bias !== null && Math.abs(s.bias) > 0.1
                      ? "amber-text"
                      : ""
                  }
                >
                  {pct(s.bias)}
                </td>
                <td>{pct(s.coverage_80)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="footnote">
        <Info size={14} /> WAPE and bias are undefined when actual demand totals
        zero. MASE is undefined for a constant seasonal training history.
      </p>
    </section>
  );
}
export function ForecastTable({ run }: { run: Run }) {
  return (
    <details className="panel detail-table">
      <summary>
        Daily forecast values{" "}
        <span className="muted">Point estimate · 80% and 95% bands</span>
      </summary>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Expected units</th>
              <th>80% lower</th>
              <th>80% upper</th>
              <th>95% lower</th>
              <th>95% upper</th>
            </tr>
          </thead>
          <tbody>
            {run.forecast.map((p) => (
              <tr key={p.date}>
                <td>{p.date}</td>
                <td>{num(p.point, 2)}</td>
                <td>{num(p.lower80, 2)}</td>
                <td>{num(p.upper80, 2)}</td>
                <td>{num(p.lower95, 2)}</td>
                <td>{num(p.upper95, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
export function Backtests({ run }: { run: Run }) {
  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">EVALUATE BEFORE YOU TRUST</span>
          <h1>Backtesting laboratory</h1>
          <p>
            Each forecast only sees the past. Every score comes from held-out
            demand.
          </p>
        </div>
        <span className="tag">3 test origins × {run.horizon} days</span>
      </div>
      <section className="panel">
        <div className="section-heading">
          <div>
            <span className="eyebrow">OUT-OF-SAMPLE</span>
            <h2>Forecast vs. what actually happened</h2>
          </div>
          <span className="tag mint">{title(run.selected_model)}</span>
        </div>
        <div className="chart-legend">
          <span>
            <i className="dot slate" />
            Actual demand
          </span>
          <span>
            <i className="dot green" />
            Held-out forecast
          </span>
          <span>
            <i className="swatch" />
            80% interval
          </span>
        </div>
        <ForecastChart run={run} backtest />
      </section>
      <div className="origins">
        {run.origins.map((o, i) => (
          <section className="panel origin" key={o.start}>
            <span className="eyebrow">
              ORIGIN 0{i + 1} · {o.start}
            </span>
            <div className="origin-score">
              {pct(o.models[run.selected_model].wape)}
              <span> WAPE</span>
            </div>
            <div className="split">
              <span>
                Bias <b>{pct(o.models[run.selected_model].bias)}</b>
              </span>
              <span>
                Coverage <b>{pct(o.models[run.selected_model].coverage_80)}</b>
              </span>
            </div>
            <p className="small muted">Training ends {o.train_end}</p>
          </section>
        ))}
      </div>
      <Leaderboard run={run} />
      <section className="callout">
        <ShieldCheck size={20} />
        <p>
          Model selection and interval calibration use three earlier origins.
          Test windows are never used to choose the winning model. Coverage is
          measured, not guaranteed under demand shifts.
        </p>
      </section>
    </>
  );
}
export function Scenarios({
  run,
  models,
  selectedModel,
  onError,
}: {
  run: Run;
  models: Model[];
  selectedModel: string;
  onError: (s: string) => void;
}) {
  const [input, setInput] = useState<ScenarioInput>({
    name: "Summer promotion",
    kind: "promotion",
    uplift_pct: 20,
    start_day: 1,
    end_day: run.horizon,
    note: "",
  });
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState("");
  const [drafted, setDrafted] = useState(false);
  const update = (patch: Partial<ScenarioInput>) => {
    setInput((v) => ({ ...v, ...patch }));
    setScenario(null);
  };
  const submit = async () => {
    setBusy(true);
    try {
      setScenario(await api<Scenario>(`/runs/${run.id}/scenarios`, input));
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  };
  const parse = async () => {
    setBusy(true);
    try {
      const m = models.find((m) => `${m.runtime}|${m.id}` === selectedModel);
      if (!m) throw new Error("Choose an installed model first.");
      const data = await api<{ draft: ScenarioInput }>("/scenario-drafts", {
        runtime: m.runtime,
        model: m.id,
        text,
      });
      setInput(data.draft);
      setScenario(null);
      setDrafted(true);
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">MAKE THE ASSUMPTION EXPLICIT</span>
          <h1>What changes the plan?</h1>
          <p>
            Explore an event, promotion, or manual adjustment against a frozen
            baseline.
          </p>
        </div>
        <span className="tag purple">Scenario workspace</span>
      </div>
      <div className="scenario-grid">
        <section className="panel scenario-form">
          <div className="section-heading">
            <h2>
              <FlaskConical size={18} /> Scenario assumptions
            </h2>
          </div>
          <label>
            Scenario name
            <input
              value={input.name}
              onChange={(e) => update({ name: e.target.value })}
              maxLength={80}
            />
          </label>
          <label>
            Event type
            <select
              value={input.kind}
              onChange={(e) =>
                update({ kind: e.target.value as ScenarioInput["kind"] })
              }
            >
              <option value="promotion">Promotion</option>
              <option value="event">Event / disruption</option>
              <option value="manual">Manual adjustment</option>
            </select>
          </label>
          <label>
            Demand adjustment (%)
            <input
              type="number"
              min={-100}
              max={300}
              value={input.uplift_pct}
              onChange={(e) => update({ uplift_pct: Number(e.target.value) })}
            />
          </label>
          <div className="form-row">
            <label>
              From day
              <input
                type="number"
                min={1}
                max={run.horizon}
                value={input.start_day}
                onChange={(e) => update({ start_day: Number(e.target.value) })}
              />
            </label>
            <label>
              Through day
              <input
                type="number"
                min={1}
                max={run.horizon}
                value={input.end_day}
                onChange={(e) => update({ end_day: Number(e.target.value) })}
              />
            </label>
          </div>
          <label>
            Planning rationale
            <textarea
              value={input.note}
              onChange={(e) => update({ note: e.target.value })}
              maxLength={500}
              placeholder="Record why this assumption is reasonable."
            />
          </label>
          {drafted && (
            <p className="small amber-text">
              AI draft — review every assumption before applying.
            </p>
          )}
          <button
            className="primary full"
            onClick={submit}
            disabled={busy || !input.name}
          >
            {busy ? "Computing…" : "Apply scenario"}
            <ArrowUpRight size={16} />
          </button>
          <details className="ai-draft">
            <summary>Draft with a local model</summary>
            <label>
              Describe your scenario
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="20% uplift from day 1 through day 7"
                maxLength={1000}
              />
            </label>
            <button
              onClick={parse}
              disabled={busy || !text || selectedModel === "none"}
            >
              Parse into reviewable draft
            </button>
            <p className="small muted">
              Select a local model in the top bar. Parsing never applies a
              change.
            </p>
          </details>
        </section>
        <div>
          <section className="panel">
            <div className="section-heading">
              <div>
                <span className="eyebrow">CONDITIONAL FORECAST</span>
                <h2>See the consequence.</h2>
              </div>
              <span className="tag">
                {run.sku} / {run.location}
              </span>
            </div>
            <div className="chart-legend">
              <span>
                <i className="dot green" />
                Baseline
              </span>
              <span>
                <i className="dot purple-dot" />
                Scenario
              </span>
            </div>
            <ForecastChart run={run} scenario={scenario} />
          </section>
          {scenario ? (
            <>
              <div className="scenario-stats">
                <div className="panel">
                  <span>Baseline total</span>
                  <strong>
                    {num(scenario.baseline_total)}
                    <small> units</small>
                  </strong>
                </div>
                <div className="panel">
                  <span>Scenario total</span>
                  <strong>
                    {num(scenario.scenario_total)}
                    <small> units</small>
                  </strong>
                </div>
                <div className="panel">
                  <span>Change in demand</span>
                  <strong className="purple-text">
                    {scenario.delta_units >= 0 ? "+" : ""}
                    {num(scenario.delta_units)}
                    <small> units</small>
                  </strong>
                </div>
              </div>
              <p className="callout">
                <Info size={18} />
                {scenario.interval_note}
              </p>
              <p className="small muted">
                Saved scenario {scenario.id} · Baseline {scenario.run_id}
              </p>
            </>
          ) : (
            <div className="empty">
              <FlaskConical size={28} />
              <h3>Your baseline is ready.</h3>
              <p>Apply an assumption to compare the two plans.</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
export function DataPage({
  datasets,
  onImported,
  onError,
}: {
  datasets: Dataset[];
  onImported: () => void;
  onError: (s: string) => void;
}) {
  const [reports, setReports] = useState<Report[]>([]);
  const [busy, setBusy] = useState(false);
  const refresh = async () => {
    try {
      setReports((await api<{ items: Report[] }>("/validation-reports")).items);
    } catch (e) {
      onError(String(e));
    }
  };
  const upload = async (file?: File) => {
    if (!file) return;
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const report = await api<Report>("/imports", form);
      setReports((r) => [report, ...r.filter((x) => x.id !== report.id)]);
      onImported();
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">TRUST STARTS AT THE SOURCE</span>
          <h1>Data & provenance</h1>
          <p>
            Versioned datasets. Visible validation. No silently dropped records.
          </p>
        </div>
        <button onClick={refresh}>Load validation reports</button>
      </div>
      <div className="data-grid">
        <section className="panel">
          <div className="section-heading">
            <h2>Dataset registry</h2>
            <span className="tag">{datasets.length} datasets</span>
          </div>
          {datasets.map((d) => (
            <div className="dataset" key={d.id}>
              <div className="split">
                <h3>{d.id}</h3>
                <span className="tag mint">Immutable</span>
              </div>
              <p>
                {num(d.record_count)} records · {d.source}
              </p>
              <p className="small muted">
                Ingested {new Date(d.created_at).toLocaleString()}
              </p>
              <code title={d.sha256}>SHA-256 {d.sha256.slice(0, 28)}…</code>
            </div>
          ))}
        </section>
        <section className="panel upload-panel">
          <Upload size={28} />
          <h2>Bring your demand history</h2>
          <p>
            UTF-8 CSV, up to 10 MiB. Each file becomes a new dataset version.
          </p>
          <label className="upload-label">
            {busy ? "Validating…" : "Choose CSV file"}
            <input
              aria-label="Upload demand CSV"
              type="file"
              accept=".csv,text/csv"
              disabled={busy}
              onChange={(e) => {
                void upload(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
          </label>
          <p className="small muted">
            Required: record_id, dataset_id, sku, location, date, demand. Daily
            observations; explicit zeros; no duplicate keys.
          </p>
        </section>
      </div>
      {reports.map((r) => (
        <section className="panel validation-report" key={r.id}>
          <div className="section-heading">
            <h2>{r.filename || r.dataset_id || "Import report"}</h2>
            <span className={`tag ${r.status === "accepted" ? "mint" : "red"}`}>
              {r.status}
            </span>
          </div>
          <div className="report-totals">
            <span>
              <b>{num(r.rows)}</b> rows read
            </span>
            <span>
              <b>{num(r.accepted)}</b> accepted
            </span>
            <span>
              <b>{num(r.rejected)}</b> rejected
            </span>
            <span>
              <b>{num(r.warnings)}</b> warnings
            </span>
          </div>
          {r.note && <p className="muted">{r.note}</p>}
          {r.issues.length > 0 && (
            <ul className="issues">
              {r.issues.map((e, i) => (
                <li key={i}>
                  <b>{e.line ? "Row " + e.line : "Dataset"}:</b> {e.message}
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
    </>
  );
}
export function About() {
  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">BUILT TO BE QUESTIONED</span>
          <h1>A forecast is a decision input.</h1>
          <p>
            DemandSense makes uncertainty, model quality, and planning
            assumptions inspectable.
          </p>
        </div>
        <span className="tag mint">Open source · local first</span>
      </div>
      <section className="panel about-hero">
        <span className="eyebrow">THE ARCHITECTURE</span>
        <div className="architecture">
          <div>
            <b>01</b>
            <h3>Demand history</h3>
            <p>
              Validated daily records
              <br />
              Stable source identifiers
            </p>
          </div>
          <ArrowUpRight />
          <div>
            <b>02</b>
            <h3>Forecast engine</h3>
            <p>
              Six competing models
              <br />
              Rolling-origin evaluation
            </p>
          </div>
          <ArrowUpRight />
          <div>
            <b>03</b>
            <h3>Planning evidence</h3>
            <p>
              Intervals & scenarios
              <br />
              Versioned downstream API
            </p>
          </div>
        </div>
        <div className="ai-boundary">
          <ShieldCheck />
          <div>
            <h3>Optional local AI lives outside the calculation path.</h3>
            <p>
              Ollama or a local llama.cpp / vLLM server can explain evidence and
              draft scenarios. Schema validation, evidence citations, and
              deterministic fallback keep model failures out of forecast state.
            </p>
          </div>
        </div>
      </section>
      <div className="about-grid">
        <section className="panel">
          <h2>What the model sees</h2>
          <p>
            Daily demand, time trend, weekly Fourier features, and known
            promotion flags. The ridge model uses exogenous features;
            intermittent models estimate demand arrivals and sizes.
          </p>
          <p>
            Synthetic ground truth and shock labels are withheld from training.
            The default forecast assumes no future promotions.
          </p>
        </section>
        <section className="panel">
          <h2>What the score means</h2>
          <p>
            Three early origins calibrate bands and select the model. Three
            later origins measure WAPE, MASE, RMSE, bias, and interval coverage.
          </p>
          <p>
            Positive bias means overforecasting. Empirical interval coverage can
            deteriorate under shocks, season shifts, and stockout censoring.
          </p>
        </section>
        <section className="panel">
          <h2>Honest boundaries</h2>
          <p>
            This is a local planning workbench, not an autonomous replenishment
            system. Daily bands are not joint lead-time distributions. Scenario
            effects are assumptions, not causal estimates.
          </p>
          <p>
            The demo is synthetic and does not establish accuracy on your
            assortment. No ERP integration, hierarchy reconciliation, or
            production SSO is claimed.
          </p>
        </section>
        <section className="panel">
          <h2>Built for inspection</h2>
          <p>
            Python · NumPy · scikit-learn · FastAPI · SQLAlchemy · PostgreSQL /
            SQLite · React · ECharts. All core calculations run without an LLM.
          </p>
          <a href="http://127.0.0.1:8027/docs" target="_blank" rel="noreferrer">
            Explore the API <ArrowUpRight size={14} />
          </a>
          <p className="small muted">
            Repository docs cover architecture, evaluation, licenses, security,
            and native development.
          </p>
        </section>
      </div>
      <section className="callout">
        <ArrowDownToLine size={20} />
        <p>
          Inventory integration uses{" "}
          <code>GET /api/v1/inventory/forecasts/&#123;run_id&#125;</code>. It
          returns versioned daily forecasts and both interval levels with
          explicit statistical semantics.
        </p>
      </section>
    </>
  );
}
