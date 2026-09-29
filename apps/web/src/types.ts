export type Page = "workspace" | "backtests" | "scenarios" | "data" | "about";
export interface Series {
  sku: string;
  location: string;
  days: number;
  units: number;
  daily_mean: number;
  start: string;
  end: string;
  promo_days: number;
  stockout_days: number;
}
export interface Point {
  date: string;
  point: number;
  lower80: number;
  upper80: number;
  lower95: number;
  upper95: number;
}
export interface Score {
  model: string;
  selected: boolean;
  wape: number | null;
  mase: number | null;
  rmse: number;
  bias: number | null;
  mae: number;
  coverage_80: number;
  coverage_95: number;
  selection_mae: number;
}
export interface Evidence {
  id: string;
  label: string;
  value: string | number | null;
  detail: string;
}
export interface Run {
  id: string;
  sku: string;
  location: string;
  dataset_id: string;
  horizon: number;
  created_at: string;
  engine_version: string;
  selected_model: string;
  metrics: Score;
  leaderboard: Score[];
  forecast: Point[];
  forecast_total: number;
  history: {
    date: string;
    demand: number;
    promotion: boolean;
    stockout: boolean;
  }[];
  backtest: {
    date: string;
    actual: number;
    point: number;
    lower80: number;
    upper80: number;
  }[];
  classification: {
    class: string;
    adi: number | null;
    cv2: number | null;
    zero_fraction: number;
  };
  origins: {
    train_end: string;
    start: string;
    models: Record<string, Score>;
  }[];
  evidence: Evidence[];
  warnings: string[];
  provenance: { source_record_count: number; source_ids_sha256: string };
}
export interface ScenarioInput {
  name: string;
  kind: "manual" | "event" | "promotion";
  uplift_pct: number;
  start_day: number;
  end_day: number;
  note: string;
}
export interface Scenario {
  id: string;
  run_id: string;
  forecast: Point[];
  baseline_total: number;
  scenario_total: number;
  delta_units: number;
  interval_note: string;
  assumptions: ScenarioInput;
}
export interface Model {
  id: string;
  runtime: string;
  size_bytes?: number;
}
export interface Report {
  id: string;
  filename?: string;
  dataset_id?: string;
  status: string;
  rows: number;
  accepted: number;
  rejected: number;
  warnings: number;
  issues: { line: number | null; code: string; message: string }[];
  note?: string;
}
export interface Dataset {
  id: string;
  record_count: number;
  source: string;
  created_at: string;
  sha256: string;
  provenance: { skus?: number; days?: number; locations?: number };
}
export interface Explanation {
  mode: string;
  narrative: {
    summary: string;
    claims: { evidence_id: string; interpretation: string }[];
    abstained: boolean;
    caveats: string[];
  };
  notice: string;
  telemetry: {
    status: string;
    latency_ms: number;
    model: string;
    runtime: string;
    validation_failures: number;
  };
}
