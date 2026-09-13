import { useEffect, useState, type FormEvent } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type RiskBand = "low" | "medium" | "high" | "critical";
type Dataset = { dataset_id: number; source_name: string; source_as_of_date: string | null; imported_at: string };
type Project = {
  project_id: number; project_code: string; snapshot_id: number; project_name: string; sector: string; ministry: string;
  implementing_agency: string; original_cost_cr: number; revised_cost_cr: number | null; expenditure_cr: number;
  physical_progress_pct: number; prediction_id: number | null; cost_risk_probability: number | null;
  time_risk_probability: number | null; implementation_score: number | null; overall_score: number | null;
  risk_band: RiskBand | null; availability_status: string; dataset: Dataset;
};
type Dashboard = {
  total_projects: number; available_predictions: number; high_risk_projects: number; critical_projects: number;
  average_overall_score: number | null; total_original_cost_cr: number; total_revised_cost_cr: number;
  total_expenditure_cr: number; dataset: Dataset | null;
};
type Detail = Project & {
  original_commissioning_date: string; revised_commissioning_date: string | null; sanction_date: string | null;
  cost_increase_cr: number | null; cost_escalation_pct: number | null; expenditure_to_original_cost_ratio: number | null;
  expenditure_to_revised_cost_ratio: number | null; schedule_revision_days: number | null; project_age_days: number | null;
  planned_duration_days: number | null; analysis_date_source: string; unavailable_reasons: Record<string, string>;
};
type Group = { group: string; project_count: number; available_prediction_count: number; average_overall_score: number | null; high_risk_projects: number; critical_projects: number };
type Benchmark = { cohort_size: number; percentile: number | null; average_cost_escalation_pct: number | null; average_expenditure_ratio: number | null; average_progress_pct: number | null; average_risk_score: number | null };
type Explanation = { component_model_version_id: number; feature_name: string; feature_value: unknown; shap_contribution: number; baseline_value: number; output_scale: string };
type AssistantResponse = { answer: string; intent: string; sources: { label: string }[]; provider_status: string; caveats: string[] };

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api";
const bandColors: Record<string, string> = { low: "#2d8b70", medium: "#d08a32", high: "#d45b45", critical: "#8e2f3d" };

function formatNumber(value: number | null | undefined, digits = 0) {
  if (value === null || value === undefined) return "Unavailable";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value);
}
function formatCrore(value: number | null | undefined) { return value === null || value === undefined ? "Unavailable" : `${formatNumber(value, 2)} cr`; }
function formatPercent(value: number | null | undefined) { return value === null || value === undefined ? "Unavailable" : `${formatNumber(value, 1)}%`; }
async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json() as Promise<T>;
}

function App() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [sector, setSector] = useState("");
  const [riskBand, setRiskBand] = useState("");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null);
  const [explanations, setExplanations] = useState<Explanation[]>([]);
  const [assistantQuestion, setAssistantQuestion] = useState("");
  const [assistantAnswer, setAssistantAnswer] = useState<AssistantResponse | null>(null);
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  useEffect(() => {
    const params = new URLSearchParams();
    if (sector) params.set("sector", sector);
    if (riskBand) params.set("risk_band", riskBand);
    const query = params.toString() ? `?${params.toString()}` : "";
    const projectQuery = params.toString() ? `&${params.toString()}` : "";
    setLoading(true);
    setError("");
    Promise.all([
      getJson<Dashboard>(`/dashboard/summary${query}`),
      getJson<{ items: Project[] }>(`/projects?limit=500${projectQuery}`),
      getJson<Group[]>(`/analytics/sectors${query}`),
    ]).then(([summary, projectResponse, sectorGroups]) => {
      setDashboard(summary); setProjects(projectResponse.items); setGroups(sectorGroups); setUpdatedAt(new Date());
    }).catch((requestError: Error) => setError(requestError.message)).finally(() => setLoading(false));
  }, [sector, riskBand]);

  useEffect(() => {
    if (selectedId === null) { setDetail(null); return; }
    setDetailLoading(true);
    Promise.all([
      getJson<Detail>(`/risk/projects/${selectedId}`),
      getJson<Benchmark>(`/analytics/benchmarks?project_id=${selectedId}`),
      getJson<{ explanations: Explanation[] }>(`/risk/projects/${selectedId}/explanation`).catch(() => ({ explanations: [] })),
    ]).then(([project, peerBenchmark, explanation]) => {
      setDetail(project); setBenchmark(peerBenchmark); setExplanations(explanation.explanations);
    }).catch((requestError: Error) => setError(requestError.message)).finally(() => setDetailLoading(false));
  }, [selectedId]);

  const visibleProjects = projects.filter((project) => {
    const query = search.toLowerCase();
    return !query || `${project.project_name} ${project.project_code} ${project.sector}`.toLowerCase().includes(query);
  });
  const scatterData = projects.filter((project) => project.cost_risk_probability !== null && project.time_risk_probability !== null).map((project) => ({
    x: (project.cost_risk_probability ?? 0) * 100, y: (project.time_risk_probability ?? 0) * 100, name: project.project_code, band: project.risk_band ?? "low",
  }));
  const sectors = Array.from(new Set(projects.map((project) => project.sector))).sort();

  async function askAssistant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!assistantQuestion.trim()) return;
    setAssistantLoading(true);
    try {
      const response = await fetch(`${API_URL}/assistant/query`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: assistantQuestion }) });
      if (!response.ok) throw new Error(`Assistant request failed (${response.status})`);
      setAssistantAnswer(await response.json() as AssistantResponse);
    } catch (requestError) {
      setAssistantAnswer({ answer: requestError instanceof Error ? requestError.message : "Assistant unavailable.", intent: "unknown", sources: [], provider_status: "disabled", caveats: [] });
    } finally { setAssistantLoading(false); }
  }

  return <div className="app-shell">
    <header className="topbar"><div className="brand-lockup"><div className="brand-mark">IR</div><div><p className="eyebrow">SIH 26103 / FIELD DESK</p><h1>Infrastructure Risk Monitor</h1></div></div><div className="topbar-meta"><span className="status-dot" /><span>{updatedAt ? `Synced ${updatedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "Awaiting data"}</span><span className="snapshot-label">SNAPSHOT VIEW</span></div></header>
    <main className="workspace">
      <section className="intro-row"><div><p className="eyebrow coral">PORTFOLIO CONTROL ROOM</p><h2>Know where attention belongs.</h2><p className="intro-copy">A live read of project exposure across cost, time, and implementation signals.</p></div><div className="data-note"><span className="note-label">DATASET STATUS</span><strong>{dashboard?.dataset?.source_name ?? "No completed dataset"}</strong><span>{dashboard?.dataset?.source_as_of_date ? `As of ${dashboard.dataset.source_as_of_date}` : "Source date unavailable"}</span></div></section>
      {error && <div className="error-banner">Could not reach the monitoring API. Start the backend and refresh to load the portfolio. <span>{error}</span></div>}
      <section className="metric-grid" aria-label="Portfolio summary"><Metric label="Projects tracked" value={dashboard ? formatNumber(dashboard.total_projects) : "--"} detail={dashboard ? `${formatNumber(dashboard.available_predictions)} scored` : "Loading portfolio"} /><Metric label="High / critical" value={dashboard ? `${dashboard.high_risk_projects} / ${dashboard.critical_projects}` : "--"} detail="Requires review" accent="coral" /><Metric label="Average risk" value={dashboard ? formatNumber(dashboard.average_overall_score, 1) : "--"} detail="Overall score / 100" accent="gold" /><Metric label="Capital exposed" value={dashboard ? formatCrore(dashboard.total_revised_cost_cr || dashboard.total_original_cost_cr) : "--"} detail="Reported project value" accent="blue" /></section>
      <section className="filter-bar" aria-label="Portfolio filters"><div className="filter-heading"><span className="eyebrow">FILTER PORTFOLIO</span><span>{visibleProjects.length} visible records</span></div><label className="search-field"><span>Find project</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name, code, or sector" /></label><label><span>Sector</span><select value={sector} onChange={(event) => setSector(event.target.value)}><option value="">All sectors</option>{sectors.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label><span>Risk band</span><select value={riskBand} onChange={(event) => setRiskBand(event.target.value)}><option value="">All bands</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label><button className="clear-button" onClick={() => { setSector(""); setRiskBand(""); setSearch(""); }}>Clear</button></section>
      {loading ? <div className="loading-state"><span className="loader" />Loading portfolio signals</div> : <div className="dashboard-grid">
        <section className="panel ranking-panel"><div className="panel-heading"><div><p className="eyebrow">PRIORITY QUEUE</p><h3>Projects requiring a closer look</h3></div><span className="panel-count">{visibleProjects.length} records</span></div>{visibleProjects.length === 0 ? <EmptyState /> : <div className="table-wrap"><table><thead><tr><th>Project</th><th>Sector</th><th>Progress</th><th>Exposure</th><th>Score</th><th>Status</th></tr></thead><tbody>{visibleProjects.map((project) => <tr key={project.project_id} className={selectedId === project.project_id ? "selected-row" : ""} onClick={() => setSelectedId(project.project_id)}><td><strong>{project.project_name}</strong><span>{project.project_code}</span></td><td>{project.sector}</td><td><div className="progress-cell"><span>{formatPercent(project.physical_progress_pct)}</span><i><b style={{ width: `${project.physical_progress_pct}%` }} /></i></div></td><td>{formatPercent(project.overall_score)}</td><td><strong className="score-number">{project.overall_score === null ? "--" : formatNumber(project.overall_score)}</strong></td><td><Band band={project.risk_band} /></td></tr>)}</tbody></table></div>}</section>
        <aside className="side-stack"><section className="panel chart-panel"><div className="panel-heading"><div><p className="eyebrow">RISK MAP</p><h3>Cost vs time exposure</h3></div></div><div className="chart-legend"><span><i className="legend-dot cost" />Cost</span><span><i className="legend-dot time" />Time</span></div><ResponsiveContainer width="100%" height={210}><ScatterChart margin={{ top: 10, right: 10, bottom: 8, left: -15 }}><CartesianGrid stroke="#d9d4c8" strokeDasharray="3 3" /><XAxis type="number" dataKey="x" name="Cost" domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" /><YAxis type="number" dataKey="y" name="Time" domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" /><Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(value) => `${formatNumber(Number(value), 1)}%`} /><Scatter data={scatterData} fill="#d45b45">{scatterData.map((point) => <Cell key={point.name} fill={bandColors[point.band]} />)}</Scatter></ScatterChart></ResponsiveContainer><div className="axis-note"><span>Lower exposure</span><span>Higher exposure</span></div></section><section className="panel chart-panel"><div className="panel-heading"><div><p className="eyebrow">SECTOR PULSE</p><h3>Average risk by sector</h3></div></div><ResponsiveContainer width="100%" height={210}><BarChart data={groups.slice(0, 7)} layout="vertical" margin={{ top: 4, right: 10, bottom: 4, left: 12 }}><CartesianGrid horizontal={false} stroke="#d9d4c8" /><XAxis type="number" domain={[0, 100]} hide /><YAxis type="category" dataKey="group" width={72} tick={{ fontSize: 10 }} /><Tooltip formatter={(value) => `${formatNumber(Number(value), 1)} / 100`} /><Bar dataKey="average_overall_score" fill="#2e6673" radius={[0, 3, 3, 0]} barSize={15} /></BarChart></ResponsiveContainer></section></aside>
      </div>}
      <section className="limitations-band"><div><p className="eyebrow">READ THE SIGNAL CORRECTLY</p><h3>Snapshot classification, not a promise about the future.</h3></div><p>Risk values are estimates from the available report snapshot. Missing revised costs, dates, or model outputs remain unavailable rather than being silently treated as safe.</p></section>
      <section className="assistant-panel"><div className="assistant-heading"><div><p className="eyebrow">GROUNDED ASSISTANT</p><h3>Ask the portfolio a question.</h3></div><span>Reads stored project facts and model outputs only</span></div><form onSubmit={askAssistant} className="assistant-form"><input value={assistantQuestion} onChange={(event) => setAssistantQuestion(event.target.value)} placeholder="Which projects have the highest stored risk?" aria-label="Ask the portfolio assistant" /><button type="submit" disabled={assistantLoading}>{assistantLoading ? "Thinking" : "Ask"}</button></form>{assistantAnswer && <div className="assistant-answer"><p>{assistantAnswer.answer}</p><div className="assistant-meta"><span>{assistantAnswer.provider_status === "groq" ? "Groq grounded response" : "Deterministic retrieved summary"}</span>{assistantAnswer.sources.length > 0 && <span>{assistantAnswer.sources.length} source references</span>}</div>{assistantAnswer.caveats.map((caveat) => <small key={caveat}>{caveat}</small>)}</div>}</section>
    </main>
    {selectedId !== null && <div className="drawer-backdrop" onClick={() => setSelectedId(null)}><aside className="detail-drawer" onClick={(event) => event.stopPropagation()}><button className="close-button" onClick={() => setSelectedId(null)} aria-label="Close project details">Close</button>{detailLoading ? <div className="loading-state"><span className="loader" />Loading project</div> : detail ? <DetailView detail={detail} benchmark={benchmark} explanations={explanations} /> : <EmptyState />}</aside></div>}
  </div>;
}

function Metric({ label, value, detail, accent = "green" }: { label: string; value: string; detail: string; accent?: string }) { return <article className={`metric metric-${accent}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>; }
function Band({ band }: { band: string | null }) { return <span className={`band band-${band ?? "unknown"}`}><i />{band ?? "Unavailable"}</span>; }
function EmptyState() { return <div className="empty-state"><strong>No matching projects</strong><span>Adjust the filters or import a completed dataset.</span></div>; }
function DetailView({ detail, benchmark, explanations }: { detail: Detail; benchmark: Benchmark | null; explanations: Explanation[] }) {
  return <div className="detail-content"><div className="detail-kicker"><span className="eyebrow">PROJECT INVESTIGATION</span><button className="code-chip">{detail.project_code}</button></div><h2>{detail.project_name}</h2><p className="detail-subtitle">{detail.sector} / {detail.ministry}</p><div className="detail-score"><div><span className="eyebrow">OVERALL RISK</span><strong>{detail.overall_score === null ? "--" : formatNumber(detail.overall_score)}</strong></div><Band band={detail.risk_band} /></div><div className="risk-trio"><RiskStat label="Cost risk" value={formatPercent(detail.cost_risk_probability === null ? null : detail.cost_risk_probability * 100)} /><RiskStat label="Time risk" value={formatPercent(detail.time_risk_probability === null ? null : detail.time_risk_probability * 100)} /><RiskStat label="Implementation" value={formatNumber(detail.implementation_score, 1)} /></div><div className="detail-section"><p className="eyebrow">OBSERVED FACTS</p><div className="fact-grid"><Fact label="Original cost" value={formatCrore(detail.original_cost_cr)} /><Fact label="Revised cost" value={formatCrore(detail.revised_cost_cr)} /><Fact label="Expenditure" value={formatCrore(detail.expenditure_cr)} /><Fact label="Progress" value={formatPercent(detail.physical_progress_pct)} /><Fact label="Cost escalation" value={formatPercent(detail.cost_escalation_pct)} /><Fact label="Schedule revision" value={detail.schedule_revision_days === null ? "Unavailable" : `${formatNumber(detail.schedule_revision_days)} days`} /></div></div><div className="detail-section"><p className="eyebrow">MODEL DRIVERS</p>{explanations.length === 0 ? <p className="muted-copy">No stored explanations are available for this prediction.</p> : <div className="driver-list">{explanations.slice(0, 5).map((item) => <div className="driver-row" key={`${item.feature_name}-${item.component_model_version_id}`}><span>{item.feature_name}</span><strong className={item.shap_contribution >= 0 ? "driver-up" : "driver-down"}>{item.shap_contribution >= 0 ? "+" : ""}{formatNumber(item.shap_contribution, 3)}</strong></div>)}</div>}</div><div className="benchmark-strip"><div><span className="eyebrow">PEER BENCHMARK</span><strong>{benchmark?.percentile === null || benchmark?.percentile === undefined ? "Not enough peers" : `Higher risk than ${formatNumber(benchmark.percentile)}% of peers`}</strong></div><span>{benchmark ? `${benchmark.cohort_size} comparable peers` : "Benchmark unavailable"}</span></div><div className="focus-callout"><span className="eyebrow">SUGGESTED MONITORING FOCUS</span><p>{detail.risk_band === "critical" || detail.risk_band === "high" ? "Prioritize a detailed implementation review using the cost, time, and progress signals above." : "Continue routine monitoring and revisit when a comparable snapshot is available."}</p></div><p className="source-note">Dataset: {detail.dataset.source_name}. Analysis date source: {detail.analysis_date_source}.</p></div>;
}
function RiskStat({ label, value }: { label: string; value: string }) { return <div><span>{label}</span><strong>{value}</strong></div>; }
function Fact({ label, value }: { label: string; value: string }) { return <div><span>{label}</span><strong>{value}</strong></div>; }
export default App;
