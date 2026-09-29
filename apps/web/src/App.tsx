import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  BarChart3,
  Boxes,
  ChevronRight,
  CircleHelp,
  Database,
  FlaskConical,
  LayoutDashboard,
  LoaderCircle,
  PanelLeftClose,
  Play,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { api, exportForecast, num, pct, setCredential, title } from "./api";
import { ForecastChart } from "./Chart";
import {
  About,
  Backtests,
  DataPage,
  ForecastTable,
  Leaderboard,
  Scenarios,
} from "./Panels";
import type { Dataset, Explanation, Model, Page, Run, Series } from "./types";

const navigation = [
  { id: "workspace", name: "Forecast workspace", icon: LayoutDashboard },
  { id: "backtests", name: "Backtesting", icon: BarChart3 },
  { id: "scenarios", name: "Scenarios", icon: FlaskConical },
  { id: "data", name: "Data & provenance", icon: Database },
  { id: "about", name: "Architecture", icon: Boxes },
] as const;
export function App() {
  const [page, setPage] = useState<Page>("workspace");
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [dataset, setDataset] = useState("");
  const [items, setItems] = useState<Series[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [location, setLocation] = useState("");
  const [run, setRun] = useState<Run | null>(null);
  const [horizon, setHorizon] = useState(14);
  const [loading, setLoading] = useState(true);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [error, setError] = useState("");
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState("none");
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [explaining, setExplaining] = useState(false);
  const [settings, setSettings] = useState(false);
  const [token, setToken] = useState("");
  const [demo, setDemo] = useState(true);
  const [compact, setCompact] = useState(false);
  const requestSeq = useRef(0);
  const hasRun = useRef(false);
  const refreshData = useCallback(async () => {
    const d = await api<{ items: Dataset[] }>("/datasets");
    setDatasets(d.items);
    setDataset((v) => v || d.items[0]?.id || "");
    if (d.items.length === 0) setLoading(false);
  }, []);
  const refreshModels = async () => {
    const d = await api<{ runtimes: { models: Model[] }[] }>("/models");
    setModels(d.runtimes.flatMap((r) => r.models));
  };
  const initialize = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const config = await api<{
        demo_mode: boolean;
        write_token: string | null;
      }>("/config");
      setDemo(config.demo_mode);
      if (config.write_token) setCredential(config.write_token);
      await Promise.all([refreshData(), refreshModels()]);
    } catch (e) {
      setError(String(e));
      setSettings(true);
      setLoading(false);
    }
  }, [refreshData]);
  useEffect(() => {
    void initialize();
  }, [initialize]);
  const forecast = useCallback(async (s: Series, did: string, h: number) => {
    const sequence = ++requestSeq.current;
    hasRun.current = true;
    setLoading(true);
    setError("");
    setExplanation(null);
    try {
      const result = await api<Run>("/runs", {
        dataset_id: did,
        sku: s.sku,
        location: s.location,
        horizon: h,
      });
      if (sequence === requestSeq.current) setRun(result);
    } catch (e) {
      if (sequence === requestSeq.current) {
        setError(String(e));
        setRun(null);
      }
    } finally {
      if (sequence === requestSeq.current) setLoading(false);
    }
  }, []);
  useEffect(() => {
    if (!dataset) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setCatalogLoading(true);
      api<{ items: Series[]; total: number }>(
        `/series?dataset_id=${encodeURIComponent(dataset)}&q=${encodeURIComponent(search)}&location=${encodeURIComponent(location)}&offset=${offset}&limit=12`,
        undefined,
        controller.signal,
      )
        .then((d) => {
          setItems(d.items);
          setTotal(d.total);
          if (!hasRun.current && d.items.length)
            void forecast(d.items[0], dataset, 14);
          if (!d.items.length && !hasRun.current) setLoading(false);
        })
        .catch((e) => {
          if (e.name !== "AbortError") setError(String(e));
        })
        .finally(() => {
          if (!controller.signal.aborted) setCatalogLoading(false);
        });
    }, 180);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [dataset, search, location, offset, forecast]);
  const explain = async () => {
    if (!run) return;
    setExplaining(true);
    try {
      const m = models.find((m) => `${m.runtime}|${m.id}` === selectedModel);
      setExplanation(
        await api<Explanation>(`/runs/${run.id}/explanations`, {
          runtime: m?.runtime || "none",
          model: m?.id || "",
        }),
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setExplaining(false);
    }
  };
  const selectedDataset = datasets.find((d) => d.id === dataset);
  const currentTotal = run?.forecast_total || 0;
  return (
    <div className={`app-shell ${compact ? "compact" : ""}`}>
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("workspace");
          }}
        >
          <span className="brand-symbol">
            <Activity size={24} />
          </span>
          <span>
            Demand<span className="brand-light">Sense</span>
            <small>PLANNING INTELLIGENCE</small>
          </span>
        </a>
        <div className="workspace-label">
          <span className="workspace-avatar">DS</span>
          <div>
            Demo workspace<small>Local environment</small>
          </div>
          <ChevronRight size={15} />
        </div>
        <span className="nav-label">WORKSPACE</span>
        <nav aria-label="Main navigation">
          {navigation.map((n) => (
            <button
              key={n.id}
              aria-label={n.name}
              title={n.name}
              className={page === n.id ? "nav-active" : ""}
              onClick={() => setPage(n.id)}
            >
              <n.icon size={18} />
              <span>{n.name}</span>
              {page === n.id && <span className="active-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-card">
            <ShieldCheck size={19} />
            <b>Your data stays here.</b>
            <p>
              Local computation.
              <br />
              No cloud AI required.
            </p>
          </div>
          <button className="quiet" onClick={() => setSettings((v) => !v)}>
            <Settings2 size={17} />
            Runtime & access
          </button>
          <div className="version">
            <span>DemandSense</span>
            <span>v0.1.0</span>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button"
              aria-label="Toggle sidebar"
              onClick={() => setCompact((v) => !v)}
            >
              <PanelLeftClose size={18} />
            </button>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <b>{navigation.find((n) => n.id === page)?.name}</b>
          </div>
          <div className="top-actions">
            <span className="demo-badge">
              {demo ? "Synthetic demo" : "Private workspace"}
            </span>
            <label className="model-control">
              <Sparkles size={15} />
              <span className="sr-only">Local AI model</span>
              <select
                aria-label="Local AI model"
                value={selectedModel}
                onChange={(e) => {
                  setSelectedModel(e.target.value);
                  setExplanation(null);
                }}
              >
                <option value="none">AI off · deterministic</option>
                {models.map((m) => (
                  <option
                    key={`${m.runtime}|${m.id}`}
                    value={`${m.runtime}|${m.id}`}
                  >
                    {m.id} · {m.runtime}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="avatar"
              aria-label="About DemandSense"
              onClick={() => setPage("about")}
            >
              DS
            </button>
          </div>
        </header>
        <main id="main-content">
          <a className="skip-link" href="#workspace-content">
            Skip to forecast
          </a>
          {error && (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={17} />
              </button>
            </div>
          )}
          {settings && (
            <section className="panel settings">
              <div className="split">
                <h2>Runtime & access</h2>
                <button
                  className="icon-button"
                  aria-label="Close settings"
                  onClick={() => setSettings(false)}
                >
                  <X size={18} />
                </button>
              </div>
              <p>
                Discover models already installed in Ollama or a local llama.cpp
                / vLLM server. Model downloads are your choice.
              </p>
              <div className="settings-controls">
                <button
                  onClick={() =>
                    void refreshModels().catch((e) => setError(String(e)))
                  }
                >
                  Refresh installed models
                </button>
                <span className="muted">
                  {models.length} local models found
                </span>
                <label>
                  API access token
                  <input
                    type="password"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder="Needed outside demo mode"
                    autoComplete="off"
                  />
                </label>
                <button
                  onClick={() => {
                    setCredential(token);
                    void initialize();
                  }}
                >
                  Connect
                </button>
              </div>
            </section>
          )}
          {page === "about" ? (
            <About />
          ) : page === "data" ? (
            <DataPage
              datasets={datasets}
              onImported={() =>
                void refreshData().catch((e) => setError(String(e)))
              }
              onError={setError}
            />
          ) : (
            <>
              {page === "workspace" && (
                <div className="page-title">
                  <div>
                    <span className="eyebrow">
                      BETTER PLANS START WITH A RANGE
                    </span>
                    <h1>Demand, with perspective.</h1>
                    <p>
                      Compare the models. Understand the uncertainty. Make the
                      call.
                    </p>
                  </div>
                  <div className="page-actions">
                    <button
                      disabled={!run || loading}
                      onClick={() =>
                        run &&
                        void exportForecast(run.id).catch((e) =>
                          setError(String(e)),
                        )
                      }
                    >
                      <ArrowDownToLine size={16} />
                      Export forecast
                    </button>
                    <button
                      className="primary"
                      disabled={!run || loading}
                      onClick={() => setPage("backtests")}
                    >
                      <Play size={14} />
                      View backtests
                    </button>
                  </div>
                </div>
              )}
              <section className="scope-bar">
                <label>
                  Dataset
                  <select
                    aria-label="Dataset"
                    value={dataset}
                    onChange={(e) => {
                      requestSeq.current++;
                      setDataset(e.target.value);
                      setRun(null);
                      setExplanation(null);
                      setOffset(0);
                      hasRun.current = false;
                      setLoading(true);
                    }}
                  >
                    {datasets.map((d) => (
                      <option key={d.id}>{d.id}</option>
                    ))}
                  </select>
                </label>
                <span className="scope-divider" />
                <span>
                  <Database size={14} />
                  {num(selectedDataset?.record_count)} observations
                </span>
                <label className="horizon-control">
                  Horizon
                  <select
                    aria-label="Forecast horizon"
                    value={horizon}
                    onChange={(e) => {
                      const h = Number(e.target.value);
                      setHorizon(h);
                      if (run)
                        void forecast(
                          { sku: run.sku, location: run.location } as Series,
                          dataset,
                          h,
                        );
                    }}
                  >
                    <option value={7}>7 days</option>
                    <option value={14}>14 days</option>
                    <option value={21}>21 days</option>
                  </select>
                </label>
                <span className="scope-status">
                  <span className="status-dot" />
                  {loading ? "Computing" : "Local engine"}
                </span>
              </section>
              {loading ? (
                <div className="loading" role="status">
                  <LoaderCircle className="spin" size={28} />
                  <h2>Building the evidence.</h2>
                  <p>
                    Fitting models, calibrating uncertainty, and evaluating
                    held-out demand.
                  </p>
                </div>
              ) : run ? (
                <>
                  {page === "backtests" ? (
                    <Backtests run={run} />
                  ) : page === "scenarios" ? (
                    <Scenarios
                      key={run.id}
                      run={run}
                      models={models}
                      selectedModel={selectedModel}
                      onError={setError}
                    />
                  ) : (
                    <>
                      <div className="kpi-grid" id="workspace-content">
                        <div className="kpi">
                          <span>
                            Forecast demand
                            <Boxes size={16} />
                          </span>
                          <strong>
                            {num(currentTotal)}
                            <small> units</small>
                          </strong>
                          <p>
                            Next {run.horizon} days · {run.location}
                          </p>
                        </div>
                        <div className="kpi">
                          <span>
                            Backtest WAPE
                            <BarChart3 size={16} />
                          </span>
                          <strong>{pct(run.metrics.wape)}</strong>
                          <p>Held-out error · lower is better</p>
                        </div>
                        <div className="kpi">
                          <span>
                            Forecast bias
                            <Activity size={16} />
                          </span>
                          <strong>{pct(run.metrics.bias)}</strong>
                          <p>
                            {run.metrics.bias === null
                              ? "Undefined at zero demand"
                              : run.metrics.bias === 0
                                ? "No net bias"
                                : run.metrics.bias > 0
                                  ? "Overforecasting on held-out demand"
                                  : "Underforecasting on held-out demand"}
                          </p>
                        </div>
                        <div className="kpi">
                          <span>
                            80% interval coverage
                            <ShieldCheck size={16} />
                          </span>
                          <strong
                            className={
                              run.metrics.coverage_80 >= 0.75
                                ? "mint-text"
                                : "amber-text"
                            }
                          >
                            {pct(run.metrics.coverage_80)}
                          </strong>
                          <p>Measured coverage · target 80%</p>
                        </div>
                      </div>
                      <div className="workbench">
                        <section className="panel assortment">
                          <div className="section-heading">
                            <h2>Demand series</h2>
                            <span className="count">{num(total)}</span>
                          </div>
                          <label className="search-box">
                            <Search size={15} />
                            <input
                              aria-label="Search SKU"
                              value={search}
                              onChange={(e) => {
                                setSearch(e.target.value);
                                setOffset(0);
                              }}
                              placeholder="Search SKU…"
                            />
                          </label>
                          <select
                            aria-label="Location filter"
                            value={location}
                            onChange={(e) => {
                              setLocation(e.target.value);
                              setOffset(0);
                            }}
                          >
                            <option value="">All locations</option>
                            {Array.from(
                              new Set([
                                "CHI",
                                "DAL",
                                "SEA",
                                ...items.map((s) => s.location),
                              ]),
                            ).map((l) => (
                              <option key={l}>{l}</option>
                            ))}
                          </select>
                          <div
                            className="series-list"
                            aria-busy={catalogLoading}
                          >
                            {items.length === 0 ? (
                              <p className="empty small">No matching series.</p>
                            ) : (
                              items.map((s) => (
                                <button
                                  key={s.sku + s.location}
                                  className={
                                    s.sku === run.sku &&
                                    s.location === run.location
                                      ? "series-selected"
                                      : ""
                                  }
                                  onClick={() =>
                                    void forecast(s, dataset, horizon)
                                  }
                                >
                                  <span className="series-icon">
                                    <Boxes size={16} />
                                  </span>
                                  <span>
                                    <b>{s.sku}</b>
                                    <small>
                                      {s.location} · {s.days} days
                                    </small>
                                  </span>
                                  <span className="series-units">
                                    {num(s.daily_mean, 1)}
                                    <small>units/day</small>
                                  </span>
                                </button>
                              ))
                            )}
                          </div>
                          <div className="pagination">
                            <button
                              aria-label="Previous series page"
                              disabled={offset === 0 || catalogLoading}
                              onClick={() =>
                                setOffset((v) => Math.max(0, v - 12))
                              }
                            >
                              ←
                            </button>
                            <span>
                              {total ? offset + 1 : 0}–
                              {Math.min(offset + 12, total)} of {num(total)}
                            </span>
                            <button
                              aria-label="Next series page"
                              disabled={offset + 12 >= total || catalogLoading}
                              onClick={() => setOffset((v) => v + 12)}
                            >
                              →
                            </button>
                          </div>
                        </section>
                        <div className="analysis-stack">
                          <section className="panel chart-panel">
                            <div className="section-heading">
                              <div>
                                <div className="chart-title">
                                  <h2>{run.sku}</h2>
                                  <span className="tag">{run.location}</span>
                                  <span className="tag subtle">
                                    {title(run.classification.class)} demand
                                  </span>
                                </div>
                                <p className="muted small">
                                  Daily demand & forward forecast
                                </p>
                              </div>
                              <span className="tag mint">
                                {title(run.selected_model)}
                              </span>
                            </div>
                            <div className="chart-legend">
                              <span>
                                <i className="dot slate" />
                                Observed
                              </span>
                              <span>
                                <i className="dot green" />
                                Forecast
                              </span>
                              <span>
                                <i className="swatch" />
                                80% interval
                              </span>
                              <span className="chart-unit">UNITS / DAY</span>
                            </div>
                            <ForecastChart run={run} />
                            <div className="chart-footer">
                              <span>
                                <span className="tag raw">Observed data</span>{" "}
                                through {run.history.at(-1)?.date}
                              </span>
                              <span>
                                <span className="tag prediction">
                                  Model prediction
                                </span>{" "}
                                {run.horizon} days ahead
                              </span>
                            </div>
                          </section>
                          <section className="panel evidence-strip">
                            <div className="evidence-mark">
                              <ShieldCheck size={22} />
                            </div>
                            <div>
                              <span className="eyebrow">
                                EVIDENCE, NOT INSTINCT
                              </span>
                              <h3>
                                {title(run.selected_model)} earned the baseline.
                              </h3>
                              <p>
                                Selected on pre-test error across six
                                candidates. Validated on {run.origins.length}{" "}
                                later origins.
                              </p>
                            </div>
                            <button
                              className="text-button"
                              onClick={() => setPage("backtests")}
                            >
                              Inspect evidence <ArrowRight size={16} />
                            </button>
                          </section>
                        </div>
                      </div>
                      <div className="lower-grid">
                        <section className="panel narrative">
                          <div className="section-heading">
                            <div>
                              <span className="eyebrow">
                                EXPLAIN THE FORECAST
                              </span>
                              <h2>A narrative with receipts.</h2>
                            </div>
                            <span
                              className={`tag ${explanation?.mode === "local_ai" ? "purple" : "subtle"}`}
                            >
                              {explanation?.mode === "local_ai"
                                ? "AI-generated"
                                : "Computed evidence"}
                            </span>
                          </div>
                          {explanation ? (
                            <>
                              <p className="narrative-summary">
                                {explanation.narrative.summary}
                              </p>
                              {explanation.narrative.claims.map((c, i) => (
                                <p className="claim" key={i}>
                                  <a href={`#evidence-${c.evidence_id}`}>
                                    {c.evidence_id}
                                  </a>
                                  {c.interpretation}
                                </p>
                              ))}
                              <p className="footnote">
                                {explanation.notice} ·{" "}
                                {num(explanation.telemetry.latency_ms)} ms ·{" "}
                                {explanation.telemetry.status}
                              </p>
                            </>
                          ) : (
                            <p className="muted">
                              Trace the selected model, measured error, recent
                              demand change, and interval coverage back to their
                              source evidence.
                            </p>
                          )}
                          <button
                            className="explain-button"
                            disabled={explaining}
                            onClick={explain}
                          >
                            <Sparkles size={16} />
                            {explaining
                              ? "Reading the evidence…"
                              : selectedModel === "none"
                                ? "Explain from computed evidence"
                                : "Explain with selected local model"}
                            <ArrowRight size={16} />
                          </button>
                        </section>
                        <section className="panel evidence-list">
                          <div className="section-heading">
                            <h2>Evidence ledger</h2>
                            <span className="tag">
                              {run.evidence.length} sources
                            </span>
                          </div>
                          {run.evidence.map((e) => (
                            <details id={`evidence-${e.id}`} key={e.id}>
                              <summary>
                                <span className="evidence-id">{e.id}</span>
                                <span>{e.label}</span>
                                <b>
                                  {typeof e.value === "number"
                                    ? e.id === "E2" || e.id === "E3"
                                      ? pct(e.value)
                                      : num(e.value, 1)
                                    : title(String(e.value ?? "Undefined"))}
                                </b>
                              </summary>
                              <p>{e.detail}</p>
                            </details>
                          ))}
                        </section>
                      </div>
                      <Leaderboard run={run} />
                      <ForecastTable run={run} />
                      <details className="limitations">
                        <summary>
                          <CircleHelp size={15} /> Planning notes & limitations
                        </summary>
                        <ul>
                          {run.warnings.map((w) => (
                            <li key={w}>{w}</li>
                          ))}
                        </ul>
                        <p>
                          Run {run.id} · {run.engine_version} ·{" "}
                          {run.provenance.source_record_count} source records
                        </p>
                      </details>
                    </>
                  )}
                </>
              ) : (
                <div className="empty">
                  <Database size={28} />
                  <h2>No forecast available</h2>
                  <p>
                    Load a dataset with enough daily history, then select a
                    series.
                  </p>
                  <label>
                    Search available series
                    <input
                      aria-label="Search available series"
                      value={search}
                      onChange={(e) => {
                        setSearch(e.target.value);
                        setOffset(0);
                      }}
                    />
                  </label>
                  <div className="series-list">
                    {items.map((s) => (
                      <button
                        key={s.sku + s.location}
                        onClick={() => void forecast(s, dataset, horizon)}
                      >
                        {s.sku} / {s.location} · {s.days} days
                      </button>
                    ))}
                  </div>
                  <button onClick={() => setPage("data")}>
                    Open data workspace
                  </button>
                </div>
              )}
            </>
          )}
          <footer>
            <span>
              DemandSense{" "}
              <span className="muted">/ Forecast with perspective.</span>
            </span>
            <span>Open source. Local first. Evidence always.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
