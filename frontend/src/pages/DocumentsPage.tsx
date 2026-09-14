import { useEffect, useState } from "react";
import { API_URL, formatNumber, getJson, type Dashboard } from "../api";

type Quality = {
  dataset_id: number; source_name: string; status: string;
  accepted_count: number; rejected_count: number; issue_count: number;
  summary: { severity: string; issue_code: string; count: number }[];
  issues: { id: number; source_row_number: number; field: string | null; issue_code: string; severity: string; message: string | null }[];
};

export default function DocumentsPage() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [quality, setQuality] = useState<Quality | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getJson<Dashboard>("/dashboard/summary")
      .then((d) => {
        setDashboard(d);
        if (d.dataset) return getJson<Quality>(`/datasets/${d.dataset.dataset_id}/quality?limit=20`);
        return null;
      })
      .then((q) => { if (q) setQuality(q); })
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <section className="section" aria-labelledby="t">
      <div className="wrap">
        <div className="section-head"><p className="section-eyebrow">Resources</p><h2 id="t">Documents and method</h2><p>Quality endpoint: <code>GET /datasets/:id/quality</code>. Every figure lists its source and date.</p></div>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <div className="panel"><div className="table-wrap"><table className="gov-table">
          <thead><tr><th scope="col">Document</th><th scope="col">Type</th><th scope="col">Updated</th><th scope="col">Action</th></tr></thead>
          <tbody>
            <tr><td><strong>{dashboard?.dataset?.source_name ?? "Projects report snapshot"}</strong><span className="meta">Dataset {dashboard?.dataset?.dataset_id ?? "—"} · Source date {dashboard?.dataset?.source_as_of_date ?? "unavailable"}</span></td><td>CSV</td><td>13 Sep 2026</td><td><a className="link" href={`${API_URL}/health`} target="_blank" rel="noreferrer">API health</a></td></tr>
            <tr><td><strong>Model evaluation notes</strong><span className="meta">DOC / ModelEvaluation.md · Held-out results, seed 42</span></td><td>MD</td><td>13 Sep 2026</td><td><a className="link" href="/analytics">See analytics</a></td></tr>
            <tr><td><strong>OpenAPI docs</strong><span className="meta">Backend Swagger UI</span></td><td>API</td><td>Live</td><td><a className="link" href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">Open /docs</a></td></tr>
          </tbody>
        </table></div></div>

        <div className="panel" style={{ marginTop: 16 }}>
          <div className="panel-head"><div><p className="section-eyebrow">Data quality</p><h3>Dataset {quality?.dataset_id ?? dashboard?.dataset?.dataset_id ?? "—"} — {quality?.status ?? "loading…"}</h3></div><span className="panel-count">{quality ? `${formatNumber(quality.accepted_count)} accepted · ${formatNumber(quality.rejected_count)} rejected` : ""}</span></div>
          <div style={{ padding: 16 }}>
            {!quality ? <p>Load a completed dataset to see grouped counts and row-level issues.</p> : (
              <>
                <div className="table-wrap"><table className="gov-table">
                  <thead><tr><th scope="col">Severity</th><th scope="col">Issue code</th><th scope="col">Count</th></tr></thead>
                  <tbody>{quality.summary.map((g) => <tr key={`${g.severity}-${g.issue_code}`}><td>{g.severity}</td><td>{g.issue_code}</td><td>{formatNumber(g.count)}</td></tr>)}</tbody>
                </table></div>
                <h4 style={{ color: "#123B73" }}>Row-level issues (first 20)</h4>
                <div className="table-wrap"><table className="gov-table">
                  <thead><tr><th scope="col">Row</th><th scope="col">Severity</th><th scope="col">Field / Code</th><th scope="col">Message</th></tr></thead>
                  <tbody>{quality.issues.map((i) => <tr key={i.id}><td>{i.source_row_number}</td><td>{i.severity}</td><td>{i.field ?? i.issue_code}</td><td>{i.message ?? "—"}</td></tr>)}</tbody>
                </table></div>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
