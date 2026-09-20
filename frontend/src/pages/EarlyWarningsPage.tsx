import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getJson, Band, acknowledgeWarningApi, closeWarningApi, type EarlyWarning } from "../api";

export default function EarlyWarningsPage() {
  const [items, setItems] = useState<EarlyWarning[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const fetchWarnings = () => {
    setLoading(true);
    getJson<{ items: EarlyWarning[] }>("/early-warnings?limit=300")
      .then((r) => setItems(r.items))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchWarnings();
  }, []);

  const handleAcknowledge = async (id: number) => {
    setActionLoading(id);
    try {
      await acknowledgeWarningApi(id);
      setItems((prev) =>
        prev.map((w) => (w.id === id ? { ...w, status: "acknowledged" } : w))
      );
    } catch (err: any) {
      alert(err?.message || "Failed to acknowledge warning.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleClose = async (id: number) => {
    setActionLoading(id);
    try {
      await closeWarningApi(id);
      setItems((prev) =>
        prev.map((w) => (w.id === id ? { ...w, status: "closed" } : w))
      );
    } catch (err: any) {
      alert(err?.message || "Failed to close warning.");
    } finally {
      setActionLoading(null);
    }
  };

  const filtered = items.filter((i) => {
    if (severityFilter && i.severity !== severityFilter) return false;
    if (statusFilter !== "all" && i.status !== statusFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      const text = `${i.project_name ?? ""} ${i.project_code ?? ""} ${i.title} ${i.type}`.toLowerCase();
      if (!text.includes(q)) return false;
    }
    return true;
  });

  const openCount = items.filter((i) => i.status === "open").length;
  const ackCount = items.filter((i) => i.status === "acknowledged").length;
  const closedCount = items.filter((i) => i.status === "closed").length;

  if (loading) {
    return (
      <section className="section">
        <div className="wrap">
          <div className="panel loading" role="status">
            <span className="spinner" /> Loading early warning signals…
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="section" aria-labelledby="ew-heading">
      <div className="wrap">
        <div className="section-head">
          <p className="section-eyebrow">Monitoring · Surveillance Intelligence</p>
          <h2 id="ew-heading">Early Warning Signals Center</h2>
          <p>
            Deterministic automated signals triggered on risk escalation, progress deviation, cost overrun, and schedule slippage. Manage surveillance triage below.
          </p>

          {/* Quick counts bar */}
          <div style={{ display: "flex", gap: 12, marginTop: 12, flexWrap: "wrap" }}>
            <span style={{ fontSize: "0.82rem", background: "var(--bg-alt)", padding: "4px 10px", borderRadius: 4, border: "1px solid var(--border)" }}>
              Total Signals: <strong>{items.length}</strong>
            </span>
            <span style={{ fontSize: "0.82rem", background: "#FEF3F2", color: "var(--error)", padding: "4px 10px", borderRadius: 4, border: "1px solid #FECDCA" }}>
              Open / Unresolved: <strong>{openCount}</strong>
            </span>
            <span style={{ fontSize: "0.82rem", background: "#EFF4FB", color: "var(--navy-700)", padding: "4px 10px", borderRadius: 4, border: "1px solid #B9C9E4" }}>
              Acknowledged: <strong>{ackCount}</strong>
            </span>
            <span style={{ fontSize: "0.82rem", background: "#F0FDF4", color: "var(--success)", padding: "4px 10px", borderRadius: 4, border: "1px solid #BBF7D0" }}>
              Closed / Resolved: <strong>{closedCount}</strong>
            </span>
          </div>
        </div>

        {error && <div className="alert alert-error" role="alert">{error}</div>}

        <div className="filters" role="search">
          <div className="field search-field">
            <span><label htmlFor="q-ew">Search Signals</label></span>
            <input
              id="q-ew"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by project name, code or issue..."
            />
          </div>

          <div className="field">
            <span><label htmlFor="status-filter">Status</label></span>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Statuses ({items.length})</option>
              <option value="open">Open Only ({openCount})</option>
              <option value="acknowledged">Acknowledged ({ackCount})</option>
              <option value="closed">Closed ({closedCount})</option>
            </select>
          </div>

          <div className="field">
            <span><label htmlFor="sev-filter">Severity</label></span>
            <select
              id="sev-filter"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
            >
              <option value="">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="watch">Watch</option>
            </select>
          </div>

          <span style={{ fontSize: "0.85rem", color: "#4B5563" }}>
            {filtered.length} matching signals
          </span>
        </div>

        {filtered.length === 0 ? (
          <div className="panel" style={{ padding: 32, textAlign: "center" }}>
            <p style={{ color: "var(--ink-2)", margin: 0 }}>
              No early warnings match the selected filters.
            </p>
          </div>
        ) : (
          <div className="panel">
            <div className="table-wrap">
              <table className="gov-table">
                <thead>
                  <tr>
                    <th scope="col" style={{ width: "28%" }}>Project</th>
                    <th scope="col" style={{ width: "12%" }}>Severity</th>
                    <th scope="col" style={{ width: "15%" }}>Signal Type</th>
                    <th scope="col" style={{ width: "25%" }}>Observation</th>
                    <th scope="col" style={{ width: "10%" }}>Status</th>
                    <th scope="col" style={{ width: "10%", textAlign: "right" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((w) => (
                    <tr key={w.id}>
                      <td>
                        <strong>{w.project_name ?? `Project #${w.project_id}`}</strong>
                        <span className="row-code">{w.project_code ?? `ID: ${w.project_id}`}</span>
                      </td>
                      <td>
                        <Band band={w.severity === "watch" ? "medium" : w.severity} />
                      </td>
                      <td style={{ fontSize: "0.82rem", textTransform: "capitalize" }}>
                        {w.type.replace(/_/g, " ")}
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, fontSize: "0.88rem", color: "var(--navy-900)" }}>{w.title}</div>
                        <div style={{ fontSize: "0.78rem", color: "var(--ink-2)", marginTop: 2 }}>{w.description}</div>
                      </td>
                      <td>
                        <span
                          style={{
                            display: "inline-block",
                            padding: "3px 8px",
                            borderRadius: 4,
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            textTransform: "uppercase",
                            background:
                              w.status === "open"
                                ? "#FEF3F2"
                                : w.status === "acknowledged"
                                ? "#EFF4FB"
                                : "#F0FDF4",
                            color:
                              w.status === "open"
                                ? "var(--error)"
                                : w.status === "acknowledged"
                                ? "var(--navy-700)"
                                : "var(--success)",
                            border: `1px solid ${
                              w.status === "open"
                                ? "#FECDCA"
                                : w.status === "acknowledged"
                                ? "#B9C9E4"
                                : "#BBF7D0"
                            }`,
                          }}
                        >
                          {w.status}
                        </span>
                      </td>
                      <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                        <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", alignItems: "center" }}>
                          {w.status === "open" && (
                            <button
                              type="button"
                              className="btn-tag btn-tag-ack"
                              disabled={actionLoading === w.id}
                              onClick={() => handleAcknowledge(w.id)}
                              title="Acknowledge signal"
                            >
                              Ack
                            </button>
                          )}
                          {w.status !== "closed" && (
                            <button
                              type="button"
                              className="btn-tag btn-tag-close"
                              disabled={actionLoading === w.id}
                              onClick={() => handleClose(w.id)}
                              title="Close signal as resolved"
                            >
                              Close
                            </button>
                          )}
                          <Link to={`/projects/${w.project_id}`} className="link" style={{ fontSize: "0.82rem" }}>
                            View →
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
