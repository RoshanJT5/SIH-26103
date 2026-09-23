import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  LayoutDashboard,
  BellRing,
  ListOrdered,
  GitCompare,
  TrendingDown,
  Sliders,
  ShieldAlert,
  Layers,
  Target,
  Check,
  CheckCheck,
  ArrowRight,
  Eye,
  RefreshCw,
} from "lucide-react";
import {
  Band,
  formatNumber,
  formatPercent,
  getJson,
  clearApiCache,
  acknowledgeWarningApi,
  closeWarningApi,
  type EarlyWarning,
  type Project,
  type Dashboard,
  type PriorityResponse,
} from "../api";

export default function MonitoringOverview() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [criticalProjects, setCriticalProjects] = useState<Project[]>([]);
  const [warnings, setWarnings] = useState<EarlyWarning[]>([]);
  const [priority, setPriority] = useState<PriorityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const loadData = (force = false) => {
    if (force) setRefreshing(true);
    else setLoading(true);

    Promise.all([
      getJson<Dashboard>("/dashboard/summary", { forceRefresh: force }).catch(() => null),
      getJson<{ items: Project[] }>("/projects?risk_band=critical&limit=6", { forceRefresh: force }).catch(() => ({ items: [] })),
      getJson<{ items: EarlyWarning[] }>("/early-warnings?status=open&limit=6", { forceRefresh: force }).catch(() => ({ items: [] })),
      getJson<PriorityResponse>("/interventions/priority?limit=5", { forceRefresh: force }).catch(() => null),
    ])
      .then(([dash, crit, warn, prio]) => {
        if (dash) setDashboard(dash);
        if (crit) setCriticalProjects(crit.items);
        if (warn) setWarnings(warn.items);
        if (prio) setPriority(prio);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => { setLoading(false); setRefreshing(false); });
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAcknowledge = async (id: number) => {
    setActionLoading(id);
    try {
      await acknowledgeWarningApi(id);
      clearApiCache("/early-warnings");
      clearApiCache("/dashboard/summary");
      setWarnings((prev) =>
        prev.map((w) => (w.id === id ? { ...w, status: "acknowledged" } : w))
      );
    } catch (err: any) {
      alert(err?.message || "Failed to acknowledge warning");
    } finally {
      setActionLoading(null);
    }
  };

  const handleClose = async (id: number) => {
    setActionLoading(id);
    try {
      await closeWarningApi(id);
      clearApiCache("/early-warnings");
      clearApiCache("/dashboard/summary");
      setWarnings((prev) => prev.filter((w) => w.id !== id));
    } catch (err: any) {
      alert(err?.message || "Failed to resolve warning");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <section className="section" aria-labelledby="monitoring-title">
      <div className="wrap">
        <div className="section-head" style={{ marginBottom: 18, display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
          <div>
            <p className="section-eyebrow">Institutional Oversight</p>
            <h1 id="monitoring-title" style={{ color: "var(--navy-900)", margin: "4px 0 8px", fontSize: "1.8rem" }}>
              Monitoring Command Center
            </h1>
            <p>
              Central hub for real-time infrastructure surveillance: active early warnings triage, critical risk watchlist, snapshot differentials, and intervention queues.
            </p>
          </div>
          <div>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => { clearApiCache(); loadData(true); }}
              disabled={refreshing}
              style={{ fontSize: "0.85rem", padding: "8px 14px", display: "inline-flex", alignItems: "center", gap: 6 }}
              title="Refresh latest data from backend"
            >
              <RefreshCw size={15} className={refreshing ? "spin-icon" : ""} /> {refreshing ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>

        {/* Subsystem Navigation Bar */}
        <div className="tabs" style={{ marginTop: 14 }}>
            <button type="button" aria-selected="true" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <LayoutDashboard size={15} /> Command Overview
            </button>
            <Link to="/early-warnings" className="nav-tab-link" style={{ padding: "10px 14px", textDecoration: "none", color: "var(--ink-2)", fontWeight: 600, fontSize: "0.9rem", display: "inline-flex", alignItems: "center", gap: 6 }}>
              <BellRing size={15} /> Early Warnings
            </Link>
            <Link to="/interventions" className="nav-tab-link" style={{ padding: "10px 14px", textDecoration: "none", color: "var(--ink-2)", fontWeight: 600, fontSize: "0.9rem", display: "inline-flex", alignItems: "center", gap: 6 }}>
              <ListOrdered size={15} /> Intervention Priority
            </Link>
            <Link to="/monitoring/changes" className="nav-tab-link" style={{ padding: "10px 14px", textDecoration: "none", color: "var(--ink-2)", fontWeight: 600, fontSize: "0.9rem", display: "inline-flex", alignItems: "center", gap: 6 }}>
              <GitCompare size={15} /> Snapshot Changes
            </Link>
            <Link to="/risk/trends" className="nav-tab-link" style={{ padding: "10px 14px", textDecoration: "none", color: "var(--ink-2)", fontWeight: 600, fontSize: "0.9rem", display: "inline-flex", alignItems: "center", gap: 6 }}>
              <TrendingDown size={15} /> Risk Trends
            </Link>
          </div>

        {error && <div className="alert alert-error" role="alert">{error}</div>}

        {/* Triage KPI Grid */}
        <div className="card-grid" style={{ marginBottom: 20 }}>
          <article className="card" style={{ borderLeft: "4px solid var(--navy-700)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.76rem", fontWeight: 700, color: "var(--ink-3)", textTransform: "uppercase" }}>Monitored Portfolio</span>
              <Layers size={18} color="var(--navy-700)" />
            </div>
            <div style={{ fontSize: "1.9rem", fontWeight: 700, color: "var(--navy-900)", margin: "4px 0" }}>
              {dashboard ? formatNumber(dashboard.total_projects) : "—"}
            </div>
            <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--ink-2)" }}>
              {dashboard ? `${formatNumber(dashboard.available_predictions)} scored projects` : "Loading…"}
            </p>
          </article>

          <article className="card" style={{ borderLeft: "4px solid var(--error)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.76rem", fontWeight: 700, color: "var(--ink-3)", textTransform: "uppercase" }}>High & Critical Watchlist</span>
              <ShieldAlert size={18} color="var(--error)" />
            </div>
            <div style={{ fontSize: "1.9rem", fontWeight: 700, color: "var(--error)", margin: "4px 0" }}>
              {dashboard ? `${dashboard.critical_projects} / ${dashboard.high_risk_projects}` : "—"}
            </div>
            <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--ink-2)" }}>
              Critical / High risk classifications
            </p>
          </article>

          <article className="card" style={{ borderLeft: "4px solid var(--saffron)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.76rem", fontWeight: 700, color: "var(--ink-3)", textTransform: "uppercase" }}>Active Warning Signals</span>
              <BellRing size={18} color="var(--saffron)" />
            </div>
            <div style={{ fontSize: "1.9rem", fontWeight: 700, color: "var(--saffron)", margin: "4px 0" }}>
              {warnings.length} open
            </div>
            <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--ink-2)" }}>
              Pending operational review
            </p>
          </article>

          <article className="card" style={{ borderLeft: "4px solid var(--teal)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.76rem", fontWeight: 700, color: "var(--ink-3)", textTransform: "uppercase" }}>Top Intervention Priority</span>
              <Target size={18} color="var(--teal)" />
            </div>
            <div style={{ fontSize: "1.35rem", fontWeight: 700, color: "var(--navy-900)", margin: "6px 0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {priority?.items?.[0]?.project_code ?? "—"}
            </div>
            <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--ink-2)" }}>
              Priority score: {priority?.items?.[0] ? formatNumber(priority.items[0].priority_score, 1) : "—"}
            </p>
          </article>
        </div>

        {/* Section 1: Live Early Warning Signals with 1-Click Triage */}
        <div className="panel" style={{ marginBottom: 24 }}>
          <div className="panel-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <p className="section-eyebrow">Real-Time Triage</p>
              <h3 style={{ margin: 0 }}>Active Early Warning Signals</h3>
            </div>
            <Link to="/early-warnings" className="link" style={{ fontSize: "0.85rem", display: "inline-flex", alignItems: "center", gap: 4 }}>
              Full Early Warnings Registry ({warnings.length}+) <ArrowRight size={14} />
            </Link>
          </div>

          <div style={{ padding: "0 4px" }}>
            {loading ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--ink-2)" }}>
                <span className="spinner" /> Loading active warnings…
              </div>
            ) : warnings.length === 0 ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--ink-2)" }}>
                No open early warnings detected. All signals acknowledged or resolved.
              </div>
            ) : (
              <div className="table-wrap">
                <table className="gov-table">
                  <thead>
                    <tr>
                      <th scope="col" style={{ width: "35%" }}>Project</th>
                      <th scope="col" style={{ width: "15%" }}>Severity & Type</th>
                      <th scope="col" style={{ width: "32%" }}>Signal Details</th>
                      <th scope="col" style={{ width: "18%", textAlign: "right" }}>Triage Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {warnings.map((w) => (
                      <tr key={w.id}>
                        <td>
                          <strong>{w.project_name || `Project #${w.project_id}`}</strong>
                          <span className="row-code">{w.project_code ?? `ID: ${w.project_id}`} · {w.sector ?? "Central Sector"}</span>
                        </td>
                        <td>
                          <span className={`band band-${w.severity === "critical" ? "critical" : w.severity === "high" ? "high" : "medium"}`}>
                            {w.severity.toUpperCase()}
                          </span>
                          <div style={{ fontSize: "0.75rem", color: "var(--ink-3)", marginTop: 4 }}>
                            {w.type.replace(/_/g, " ")}
                          </div>
                        </td>
                        <td>
                          <div style={{ fontWeight: 600, fontSize: "0.88rem", color: "var(--navy-900)" }}>{w.title}</div>
                          <div style={{ fontSize: "0.78rem", color: "var(--ink-2)", marginTop: 2 }}>{w.description}</div>
                        </td>
                        <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                          <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", alignItems: "center" }}>
                            {w.status === "open" && (
                              <button
                                type="button"
                                className="btn-tag btn-tag-ack"
                                disabled={actionLoading === w.id}
                                onClick={() => handleAcknowledge(w.id)}
                                title="Mark as acknowledged by monitoring authority"
                                style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
                              >
                                {actionLoading === w.id ? "…" : <><Check size={12} /> Acknowledge</>}
                              </button>
                            )}
                            <button
                              type="button"
                              className="btn-tag btn-tag-close"
                              disabled={actionLoading === w.id}
                              onClick={() => handleClose(w.id)}
                              title="Resolve and close early warning"
                              style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
                            >
                              <CheckCheck size={12} /> Resolve
                            </button>
                            <Link to={`/projects/${w.project_id}`} className="link" style={{ fontSize: "0.82rem", alignSelf: "center", marginLeft: 4, display: "inline-flex", alignItems: "center", gap: 3 }}>
                              Inspect <ArrowRight size={12} />
                            </Link>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Section 2: Critical Risk Watchlist */}
        <div className="panel" style={{ marginBottom: 24 }}>
          <div className="panel-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <p className="section-eyebrow">Risk Classification</p>
              <h3 style={{ margin: 0 }}>Critical Risk Portfolio Watchlist</h3>
            </div>
            <Link to="/projects?risk_band=critical" className="link" style={{ fontSize: "0.85rem", display: "inline-flex", alignItems: "center", gap: 4 }}>
              View All Critical Projects <ArrowRight size={14} />
            </Link>
          </div>

          <div style={{ padding: "0 4px" }}>
            {loading ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--ink-2)" }}>
                <span className="spinner" /> Loading critical watchlist…
              </div>
            ) : criticalProjects.length === 0 ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--ink-2)" }}>
                No projects currently categorized under Critical Risk band.
              </div>
            ) : (
              <div className="table-wrap">
                <table className="gov-table">
                  <thead>
                    <tr>
                      <th scope="col">Project Code & Name</th>
                      <th scope="col">Sector / Ministry</th>
                      <th scope="col">Physical Progress</th>
                      <th scope="col">Overall Score</th>
                      <th scope="col">Risk Band</th>
                      <th scope="col" style={{ textAlign: "right" }}>Detailed Audit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {criticalProjects.map((p) => (
                      <tr key={p.project_id}>
                        <td>
                          <strong>{p.project_name}</strong>
                          <span className="row-code">{p.project_code} · {p.implementing_agency}</span>
                        </td>
                        <td>
                          <div>{p.sector}</div>
                          <span style={{ fontSize: "0.75rem", color: "var(--ink-3)" }}>{p.ministry}</span>
                        </td>
                        <td>{formatPercent(p.physical_progress_pct)}</td>
                        <td>
                          <strong style={{ color: "var(--error)" }}>
                            {p.overall_score !== null ? formatNumber(p.overall_score) : "—"}
                          </strong>
                        </td>
                        <td><Band band={p.risk_band} /></td>
                        <td style={{ textAlign: "right" }}>
                          <Link to={`/projects/${p.project_id}`} className="btn btn-secondary" style={{ padding: "4px 10px", fontSize: "0.8rem", minHeight: 32, display: "inline-flex", alignItems: "center", gap: 4 }}>
                            Analyze <ArrowRight size={13} />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Section 3: Monitoring Deep Dives */}
        <h3 style={{ color: "var(--navy-900)", marginBottom: 12, fontSize: "1.15rem" }}>
          Specialized Monitoring Frameworks
        </h3>
        <div className="card-grid">
          <article className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <GitCompare size={20} color="var(--navy-700)" />
              <h3 style={{ margin: 0 }}>Snapshot Diff Engine</h3>
            </div>
            <p style={{ fontSize: "0.86rem", color: "var(--ink-2)" }}>
              Compare current completed flash reports against previous reporting cycles to trace project escalations, score shifts, and newly elevated risks.
            </p>
            <Link className="link" to="/monitoring/changes" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              Launch Comparison Engine <ArrowRight size={14} />
            </Link>
          </article>

          <article className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <ListOrdered size={20} color="var(--navy-700)" />
              <h3 style={{ margin: 0 }}>Intervention Priority Queue</h3>
            </div>
            <p style={{ fontSize: "0.86rem", color: "var(--ink-2)" }}>
              Multi-factor objective ranking prioritizing administrative review based on cost exposure, schedule variance, and strategic weight.
            </p>
            <Link className="link" to="/interventions" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              Inspect Priority Queue <ArrowRight size={14} />
            </Link>
          </article>

          <article className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <TrendingDown size={20} color="var(--navy-700)" />
              <h3 style={{ margin: 0 }}>Longitudinal Risk Trends</h3>
            </div>
            <p style={{ fontSize: "0.86rem", color: "var(--ink-2)" }}>
              Trajectory analysis identifying projects deteriorating across sequential reporting cycles before severe milestones lapse.
            </p>
            <Link className="link" to="/risk/trends" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              Track Deteriorating Trends <ArrowRight size={14} />
            </Link>
          </article>

          <article className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <Sliders size={20} color="var(--navy-700)" />
              <h3 style={{ margin: 0 }}>Counterfactual Simulation</h3>
            </div>
            <p style={{ fontSize: "0.86rem", color: "var(--ink-2)" }}>
              Evaluate "what-if" policy interventions, budget injections, or progress catch-ups in an isolated sandbox environment.
            </p>
            <Link className="link" to="/simulation" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              Run Policy Simulation <ArrowRight size={14} />
            </Link>
          </article>
        </div>
      </div>
    </section>
  );
}
