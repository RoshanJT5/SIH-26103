import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getJson, type TrendResponse } from "../api";

export default function TrendsPage() {
  const [data, setData] = useState<TrendResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    getJson<TrendResponse>("/risk/trends?limit=20").then(setData).catch((e: Error) => setError(e.message)).finally(() => setLoading(false));
  }, []);
  if (loading) return <section className="section"><div className="wrap"><div className="panel loading" role="status"><span className="spinner" />Loading risk trends…</div></div></section>;
  if (error) return <section className="section"><div className="wrap"><div className="alert alert-error" role="alert">Unable to load trends. {error}</div></div></section>;
  return (
    <section className="section">
      <div className="wrap">
        <div className="section-head"><p className="section-eyebrow">Monitoring</p><h1 style={{ color: "#0D3157", margin: "6px 0" }}>Risk Trends</h1><p>Score movement across snapshots. Thresholds: <code>{data?.version}</code>.</p></div>
        <div className="panel"><div className="table-wrap"><table className="gov-table">
          <thead><tr><th>Project</th><th>History</th><th>Change</th><th>Trend</th></tr></thead>
          <tbody>{(data?.items ?? []).map((r) => (
            <tr key={r.project_id}><td><strong>{r.project_name}</strong><span className="row-code">{r.project_code}</span></td><td>{r.history.map((h) => h.overall_score ?? "—").join(" → ")}</td><td>{r.score_change === null ? "—" : `${r.score_change > 0 ? "+" : ""}${r.score_change}`}</td><td><Link className="link" to={`/projects/${r.project_id}`}>View</Link> · {r.trend}</td></tr>
          ))}</tbody>
        </table></div></div>
      </div>
    </section>
  );
}
