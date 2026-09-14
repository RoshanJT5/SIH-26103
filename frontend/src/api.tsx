export type RiskBand = "low" | "medium" | "high" | "critical";
export type Dataset = { dataset_id: number; source_name: string; source_as_of_date: string | null; imported_at: string };
export type Project = {
  project_id: number; project_code: string; snapshot_id: number; project_name: string; sector: string; ministry: string;
  implementing_agency: string; original_cost_cr: number; revised_cost_cr: number | null; expenditure_cr: number;
  physical_progress_pct: number; prediction_id: number | null; cost_risk_probability: number | null;
  time_risk_probability: number | null; implementation_score: number | null; overall_score: number | null;
  risk_band: RiskBand | null; availability_status: string; dataset: Dataset;
};
export type Dashboard = {
  total_projects: number; available_predictions: number; high_risk_projects: number; critical_projects: number;
  average_overall_score: number | null; total_original_cost_cr: number; total_revised_cost_cr: number;
  total_expenditure_cr: number; dataset: Dataset | null;
};
export type Detail = Project & {
  original_commissioning_date: string; revised_commissioning_date: string | null; sanction_date: string | null;
  cost_increase_cr: number | null; cost_escalation_pct: number | null; expenditure_to_original_cost_ratio: number | null;
  expenditure_to_revised_cost_ratio: number | null; schedule_revision_days: number | null; project_age_days: number | null;
  planned_duration_days: number | null; analysis_date_source: string; unavailable_reasons: Record<string, string>;
};
export type Group = { group: string; project_count: number; available_prediction_count: number; average_overall_score: number | null; high_risk_projects: number; critical_projects: number };
export type Benchmark = { cohort_size: number; percentile: number | null; average_cost_escalation_pct: number | null; average_expenditure_ratio: number | null; average_progress_pct: number | null; average_risk_score: number | null };
export type Explanation = { component_model_version_id: number; feature_name: string; feature_value: unknown; shap_contribution: number; baseline_value: number; output_scale: string };
export type AssistantResponse = { answer: string; intent: string; sources: { label: string }[]; provider_status: string; caveats: string[] };
export type Health = { status: string; database: string; assistant_enabled: boolean };
export type Alerts = { items: { id: number; severity: string; message: string | null }[]; page: { offset: number; limit: number; total: number } };
export type DatasetListItem = { dataset_id: number; source_name: string; source_as_of_date: string | null; imported_at: string; status: string; accepted_count: number; rejected_count: number };
export type SnapshotComparison = {
  version: string;
  current_dataset: { dataset_id: number; source_name: string; source_as_of_date: string | null; imported_at: string; status: string };
  previous_dataset: { dataset_id: number; source_name: string; source_as_of_date: string | null; imported_at: string; status: string } | null;
  portfolio: { project_count: number; project_count_change: number | null; high_risk_projects: number; high_risk_change: number | null; critical_projects: number; critical_change: number | null; average_overall_score: number | null; average_score_change: number | null; total_revised_cost_cr: number; revised_cost_change: number | null; total_expenditure_cr: number; expenditure_change: number | null };
  new_high_risk_projects: { project_id: number; project_code: string; project_name: string; sector: string; ministry: string; previous_score: number | null; current_score: number | null; score_change: number | null; previous_band: string | null; current_band: string | null }[];
  new_critical_projects: SnapshotComparison["new_high_risk_projects"];
  improved_projects: SnapshotComparison["new_high_risk_projects"];
  deteriorated_projects: SnapshotComparison["new_high_risk_projects"];
  new_warnings: { id: number; severity: string; message: string; deduplication_key: string }[];
  score_history: { dataset_id: number; source_name: string; source_as_of_date: string | null; project_count: number; average_overall_score: number | null; high_risk_projects: number; critical_projects: number }[];
  unavailable_reason: string | null;
};

export const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api";
export const bandColors: Record<string, string> = { low: "#16803C", medium: "#E8890C", high: "#C0531A", critical: "#C53030" };

export function formatNumber(value: number | null | undefined, digits = 0) {
  if (value === null || value === undefined) return "Unavailable";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value);
}
export function formatCrore(value: number | null | undefined) { return value === null || value === undefined ? "Unavailable" : `${formatNumber(value, 2)} cr`; }
export function formatPercent(value: number | null | undefined) { return value === null || value === undefined ? "Unavailable" : `${formatNumber(value, 1)}%`; }
export type TrendResponse = { version: string; thresholds: Record<string,string>; items: { project_id:number; project_code:string; project_name:string; sector:string; ministry:string; history:{dataset_id:number; source_as_of_date:string|null; overall_score:number|null; risk_band:string|null}[]; first_score:number|null; last_score:number|null; score_change:number|null; trend:string}[]; page:{offset:number;limit:number;total:number}};
export type PriorityResponse = { version:string; formula:string; items:{project_id:number; project_code:string; project_name:string; sector:string; ministry:string; overall_score:number|null; risk_band:string|null; priority_score:number; rank:number; drivers:{factor:string; weight:number; contribution:number; detail:string}[]}[]; page:{offset:number;limit:number;total:number}};
export type EarlyWarning = { id:number; project_id:number; type:string; severity:string; title:string; description:string; status:string; project_code:string|null; project_name:string|null; sector:string|null; ministry:string|null};
export type CostDriver = { feature:string; average_shap:number; coverage:number; interpretation:string};
export type Forecast = { project_id:number; project_code:string; methodology:string; limitations:string[]; points:{dataset_id:number|null; source_as_of_date:string|null; overall_score:number|null; is_forecast:boolean; method:string}[]};
export type Recommendations = { project_id:number; project_code:string; methodology:string; items:{priority:number; action:string; rationale:string; evidence:string}[]; limitations:string[]};
export type Confidence = { project_id:number; confidence:number|null; probability:number|null; data_quality:string; data_quality_score:number|null; limitations:string[]; unavailable_reasons:Record<string,string>; availability_status:string};
export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json() as Promise<T>;
}
export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { method:"POST", headers:{ "Content-Type":"application/json" }, body: JSON.stringify(body)});
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json() as Promise<T>;
}
export function Band({ band }: { band: string | null }) { return <span className={`band band-${band ?? "unknown"}`}><i aria-hidden="true" />{band ?? "Unavailable"}</span>; }
