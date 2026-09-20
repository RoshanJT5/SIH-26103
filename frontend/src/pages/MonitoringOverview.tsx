import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Band,
  formatNumber,
  formatPercent,
  getJson,
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
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      getJson<Dashboard>("/dashboard/summary").catch(() => null),
      getJson<{ items: Project[] }>("/projects?risk_band=critical&limit=6").catch(() => ({ items: [] })),
      getJson<{ items: EarlyWarning[] }>("/early-warnings?status=open&limit=6").catch(() => ({ items: [] })),
      getJson<PriorityResponse>("/interventions/priority?limit=5").catch(() => null),
    ])
      .then(([dash, crit, warn, prio]) => {
        if (dash) setDashboard(dash);
        if (crit) setCriticalProjects(crit.items);
        if (warn) setWarnings(warn.items);
        if (prio) setPriority(prio);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAcknowledge = async (id: number) => {
    setActionLoading(id);
    try {
      await acknowledgeWarningApi(id);
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
        <div className="section-head" style={{ marginBottom: 18 }}>
          <p className="section-eyebrow">Institutional Oversight</p>
          <h1 id="monitoring-title" style={{ color: "var(--navy-900)", margin: "4px 0 8px", fontSize: "1.8rem" }}>
            Monitoring Command Center
          </h1>
          <p>
            Central hub for real-time infrastructure surveillance: active early warnings triage, critical risk watchlist, snapshot differentials, and intervention queues.
          </p>

          {/* Subsystem Navigation Bar */}
          <div className="tabs" style={{ marginTop: 14 }}>
            <button type="button" aria-selected="true">
              Command Overview
            </button>
            <Link to="/early-warnings" className="nav-tab-link" style={{ padding: "10px 14px", textDecoration: "none", color: "var(--ink-2)", fontWeight: 600, fontSize: "0.9rem" }}>
              Early Warnings Repository
            </Link>
            <Link to="/interventions" className="nav-tab-link" style={{ padding: "10px 14px", textDecoration: "none", color: "var(--ink-2)", fontWeight: 600, fontSize: "0.9rem" }}>
              Intervention Priority Queue
            </Link>
            <Link to="/monitoring/changes" className="nav-tab-link" style={{ padding: "10px 14px", textDecoration: "none", color: "var(--ink-2)", fontWeight: 600, fontSize: "0.9rem" }}>
              Snapshot Changes
            </Link>
            <Link to="/risk/trends" className="nav-tab-link" style={{ padding: "10px 14px", textDecoration: "none", color: "var(--ink-2)", fontWeight: 600, fontSize: "0.9rem" }}>
              Risk Trends
            </Link>
          </div>
        </div>

        {error && <div className="alert alert-error" role="alert">{error}</div>}

        {/* Triage KPI Grid */}
        <div className="card-grid" style={{ marginBottom: 20 }}>
          <article className="card" style={{ borderLeft: "4px solid var(--navy-700)" }}>
            <span style={{ fontSize: "0.76rem", fontWeight: 700, color: "var(--ink-3)", textTransform: "uppercase" }}>Monitored Portfolio</span>
            <div style={{ fontSize: "1.9rem", fontWeight: 700, color: "var(--navy-900)", margin: "4px 0" }}>
              {dashboard ? formatNumber(dashboard.total_projects) : "—"}
            </div>
            <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--ink-2)" }}>
              {dashboard ? `${formatNumber(dashboard.available_predictions)} scored projects` : "Loading…"}
            </p>
          </article>

          <article className="card" style={{ borderLeft: "4px solid var(--error)" }}>
            <span style={{ fontSize: "0.76rem", fontWeight: 700, color: "var(--ink-3)", textTransform: "uppercase" }}>High & Critical Watchlist</span>
            <div style={{ fontSize: "1.9rem", fontWeight: 700, color: "var(--error)", margin: "4px 0" }}>
              {dashboard ? `${dashboard.critical_projects} / ${dashboard.high_risk_projects}` : "—"}
            </div>
            <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--ink-2)" }}>
              Critical / High risk classifications
            </p>
          </article>

          <article className="card" style={{ borderLeft: "4px solid var(--saffron)" }}>
            <span style={{ fontSize: "0.76rem", fontWeight: 700, color: "var(--ink-3)", textTransform: "uppercase" }}>Active Warning Signals</span>
            <div style={{ fontSize: "1.9rem", fontWeight: 700, color: "var(--saffron)", margin: "4px 0" }}>
              {warnings.length} open
            </div>
            <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--ink-2)" }}>
              Pending operational review
            </p>
          </article>

          <article className="card" style={{ borderLeft: "4px solid var(--teal)" }}>
            <span style={{ fontSize: "0.76rem", fontWeight: 700, color: "var(--ink-3)", textTransform: "uppercase" }}>Top Intervention Priority</span>
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
            <Link to="/early-warnings" className="link" style={{ fontSize: "0.85rem" }}>
              Full Early Warnings Registry ({warnings.length}+) →
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
                          <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                            {w.status === "open" && (
                              <button
                                type="button"
                                className="btn-tag btn-tag-ack"
                                disabled={actionLoading === w.id}
                                onClick={() => handleAcknowledge(w.id)}
                                title="Mark as acknowledged by monitoring authority"
                              >
                                {actionLoading === w.id ? "…" : "Acknowledge"}
                              </button>
                            )}
                            <button
                              type="button"
                              className="btn-tag btn-tag-close"
                              disabled={actionLoading === w.id}
                              onClick={() => handleClose(w.id)}
                              title="Resolve and close early warning"
                            >
                              Resolve
                            </button>
                            <Link to={`/projects/${w.project_id}`} className="link" style={{ fontSize: "0.82rem", alignSelf: "center", marginLeft: 4 }}>
                              Inspect →
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
            <Link to="/projects?risk_band=critical" className="link" style={{ fontSize: "0.85rem" }}>
              View All Critical Projects →
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
                          <Link to={`/projects/${p.project_id}`} className="btn btn-secondary" style={{ padding: "4px 10px", fontSize: "0.8rem", minHeight: 32 }}>
                            Analyze →
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
            <h3>Snapshot Diff Engine</h3>
            <p style={{ fontSize: "0.86rem", color: "var(--ink-2)" }}>
              Compare current completed flash reports against previous reporting cycles to trace project escalations, score shifts, and newly elevated risks.
            </p>
            <Link className="link" to="/monitoring/changes">
              Launch Comparison Engine →
            </Link>
          </article>

          <article className="card">
            <h3>Intervention Priority Queue</h3>
            <p style={{ fontSize: "0.86rem", color: "var(--ink-2)" }}>
              Multi-factor objective ranking prioritizing administrative review based on cost exposure, schedule variance, and strategic weight.
            </p>
            <Link className="link" to="/interventions">
              Inspect Priority Queue →
            </Link>
          </article>

          <article className="card">
            <h3>Longitudinal Risk Trends</h3>
            <p style={{ fontSize: "0.86rem", color: "var(--ink-2)" }}>
              Trajectory analysis identifying projects deteriorating across sequential reporting cycles before severe milestones lapse.
            </p>
            <Link className="link" to="/risk/trends">
              Track Deteriorating Trends →
            </Link>
          </article>

          <article className="card">
            <h3>Counterfactual Simulation</h3>
            <p style={{ fontSize: "0.86rem", color: "var(--ink-2)" }}>
              Evaluate "what-if" policy interventions, budget injections, or progress catch-ups in an isolated sandbox environment.
            </p>
            <Link className="link" to="/simulation">
              Run Policy Simulation →
            </Link>
          </article>
        </div>
      </div>
    </section>
  );
}
