import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link } from "react-router-dom";
import { Band, formatCrore, formatNumber, getJson, type DatasetListItem, type SnapshotComparison } from "../api";

function delta(value: number | null | undefined, change: number | null | undefined, fmt: (v: number) => string) {
  if (change === null || change === undefined) return <span style={{ color: "#6B7280" }}>—</span>;
  const arrow = change > 0 ? "↑" : change < 0 ? "↓" : "→";
  const color = change > 0 ? "#B42318" : change < 0 ? "#16803C" : "#52606D";
  const label = change > 0 ? "Increased" : change < 0 ? "Decreased" : "Stable";
  return <span style={{ color, fontWeight: 700 }} title={label}>{arrow} {change > 0 ? "+" : ""}{fmt(change)}</span>;
}

export default function ChangesPage() {
  const [datasets, setDatasets] = useState<DatasetListItem[]>([]);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [previousId, setPreviousId] = useState<number | null>(null);
  const [sector, setSector] = useState("");
  const [comparison, setComparison] = useState<SnapshotComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getJson<DatasetListItem[]>("/datasets").then((items) => {
      const completed = items.filter((d) => d.status === "completed");
      setDatasets(completed);
      if (completed.length >= 1 && currentId === null) setCurrentId(completed[0].dataset_id);
      if (completed.length >= 2 && previousId === null) setPreviousId(completed[1].dataset_id);
    }).catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (currentId === null) return;
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    params.set("current_dataset_id", String(currentId));
    if (previousId !== null && previousId !== currentId) params.set("previous_dataset_id", String(previousId));
    if (sector) params.set("sector", sector);
    getJson<SnapshotComparison>(`/monitoring/snapshot-comparison?${params.toString()}`)
      .then(setComparison)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [currentId, previousId, sector]);

  const historyData = useMemo(
    () => (comparison?.score_history ?? []).map((h) => ({ date: h.source_as_of_date ?? String(h.dataset_id), avg: h.average_overall_score, high: h.high_risk_projects })),
    [comparison],
  );

  return (
    <section className="section" aria-labelledby="t">
      <div className="wrap">
        <div className="section-head"><p className="section-eyebrow">Monitoring</p><h2 id="t">Monitoring Changes</h2><p>What changed since the previous monitoring cycle. Matched by stable project identity — not by row position.</p></div>

        <div className="filters" role="search" aria-label="Choose snapshots">
          <div className="field"><span><label htmlFor="current">Current snapshot</label></span>
            <select id="current" value={currentId ?? ""} onChange={(e) => setCurrentId(Number(e.target.value) || null)}>
              {datasets.map((d) => <option key={d.dataset_id} value={d.dataset_id}>{d.source_name} — {d.source_as_of_date ?? "undated"}</option>)}
            </select>
          </div>
          <div className="field"><span><label htmlFor="prev">Previous snapshot</label></span>
            <select id="prev" value={previousId ?? ""} onChange={(e) => setPreviousId(Number(e.target.value) || null)}>
              <option value="">Auto (previous completed)</option>
              {datasets.map((d) => <option key={d.dataset_id} value={d.dataset_id}>{d.source_name} — {d.source_as_of_date ?? "undated"}</option>)}
            </select>
          </div>
          <div className="field"><span><label htmlFor="sector">Sector</label></span>
            <select id="sector" value={sector} onChange={(e) => setSector(e.target.value)}><option value="">All sectors</option><option value="Roads">Roads</option><option value="Rail">Rail</option><option value="Water">Water</option></select>
          </div>
        </div>

        {comparison && (
          <div style={{ marginBottom: 12, fontSize: "1.05rem", fontWeight: 700, color: "#0D3157" }}>
            {comparison.current_dataset.source_as_of_date ?? comparison.current_dataset.source_name}
            {" vs "}
            {comparison.previous_dataset ? (comparison.previous_dataset.source_as_of_date ?? comparison.previous_dataset.source_name) : "no previous snapshot"}
          </div>
        )}

        {error && <div className="alert alert-error" role="alert">{error}</div>}
        {loading ? <div className="panel loading" role="status"><span className="spinner" />Loading comparison…</div> : comparison && (
          <>
            {comparison.unavailable_reason && <div className="alert alert-info" role="status">{comparison.unavailable_reason}</div>}

            <section aria-labelledby="portfolio">
              <h3 id="portfolio" style={{ color: "#0D3157" }}>Portfolio Change</h3>
              <div className="card-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
                <article className="card"><h3>Projects</h3><p style={{ fontSize: "1.6rem", fontWeight: 700 }}>{formatNumber(comparison.portfolio.project_count)} {delta(comparison.portfolio.project_count, comparison.portfolio.project_count_change, (v) => String(v))}</p></article>
                <article className="card"><h3>High / Critical</h3><p style={{ fontSize: "1.4rem", fontWeight: 700 }}>{comparison.portfolio.high_risk_projects} / {comparison.portfolio.critical_projects}</p><p>{delta(comparison.portfolio.high_risk_projects, comparison.portfolio.high_risk_change, (v) => String(v))} high · {delta(comparison.portfolio.critical_projects, comparison.portfolio.critical_change, (v) => String(v))} critical</p></article>
                <article className="card"><h3>Capital</h3><p style={{ fontSize: "1.4rem", fontWeight: 700 }}>{formatCrore(comparison.portfolio.total_revised_cost_cr)}</p><p>{delta(null, comparison.portfolio.revised_cost_change, (v) => formatCrore(v))} revised · {delta(null, comparison.portfolio.expenditure_change, (v) => formatCrore(v))} expenditure</p></article>
              </div>
            </section>

            <section aria-labelledby="movement" style={{ marginTop: 20 }}>
              <h3 id="movement" style={{ color: "#0D3157" }}>Risk Movement</h3>
              <div className="panel"><div style={{ padding: "6px 14px 14px" }}>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={historyData}>
                    <CartesianGrid stroke="#D9E1EA" strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="avg" name="Avg score" stroke="#164A7A" strokeWidth={2} dot={{ fill: "#F39A24", r: 3 }} />
                    <Line type="monotone" dataKey="high" name="High-risk count" stroke="#C98A2E" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
                <p style={{ fontSize: "0.78rem", color: "#52606D", margin: 0 }}>Units: score / 100 and project count. Source: completed snapshots. Method: {comparison.version}.</p>
              </div></div>
            </section>

            <section style={{ marginTop: 20, display: "grid", gap: 16 }}>
              {[["New High-Risk Projects", comparison.new_high_risk_projects], ["New Critical Projects", comparison.new_critical_projects], ["Deteriorating Projects", comparison.deteriorated_projects], ["Improved Projects", comparison.improved_projects]].map(([title, items]) => (
                <div key={String(title)} className="panel">
                  <div className="panel-head"><div><p className="section-eyebrow">{String(title)}</p><h3>{String(title)}</h3></div><span className="panel-count">{(items as SnapshotComparison["new_high_risk_projects"]).length} projects</span></div>
                  <div className="table-wrap"><table className="gov-table">
                    <thead><tr><th scope="col">Project</th><th scope="col">Previous → Current</th><th scope="col">Change</th><th scope="col">Action</th></tr></thead>
                    <tbody>{(items as SnapshotComparison["new_high_risk_projects"]).length === 0 ? <tr><td colSpan={4}>None in this comparison.</td></tr> : (items as SnapshotComparison["new_high_risk_projects"]).map((p) => (
                      <tr key={p.project_id}><td><strong>{p.project_name}</strong><span className="row-code">{p.project_code} · {p.sector}</span></td><td>{p.previous_band ?? "—"} → {p.current_band ?? "—"}</td><td>{p.score_change === null ? "—" : `${p.score_change > 0 ? "+" : ""}${formatNumber(p.score_change, 2)}`} {p.score_change !== null && <span style={{ color: p.score_change > 0 ? "#B42318" : "#16803C" }}>{p.score_change > 0 ? "↑" : "↓"}</span>}</td><td><Link className="link" to={`/projects/${p.project_id}`}>View →</Link></td></tr>
                    ))}</tbody>
                  </table></div>
                </div>
              ))}
            </section>

            <section style={{ marginTop: 20 }}>
              <h3 style={{ color: "#0D3157" }}>New Warnings</h3>
              {comparison.new_warnings.length === 0 ? <p>No warnings linked to newly deteriorating projects in this comparison.</p> : (
                <div className="panel"><div className="table-wrap"><table className="gov-table">
                  <thead><tr><th scope="col">Alert</th><th scope="col">Severity</th><th scope="col">Status</th></tr></thead>
                  <tbody>{comparison.new_warnings.map((w) => <tr key={w.id}><td>{w.message}</td><td><Band band={w.severity === "watch" ? "medium" : w.severity} /></td><td>{w.deduplication_key.slice(0, 8)}…</td></tr>)}</tbody>
                </table></div></div>
              )}
            </section>
          </>
        )}
      </div>
    </section>
  );
}
