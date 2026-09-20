import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { TrendingDown, TrendingUp, Minus, ArrowRight } from "lucide-react";
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
        <div className="section-head">
          <p className="section-eyebrow">Monitoring</p>
          <h1 style={{ color: "#0D3157", margin: "6px 0", display: "flex", alignItems: "center", gap: 8 }}>
            <TrendingDown size={26} color="var(--navy-700)" /> Risk Trends
          </h1>
          <p>Score movement across snapshots. Thresholds: <code>{data?.version}</code>.</p>
        </div>
        <div className="panel"><div className="table-wrap"><table className="gov-table">
          <thead><tr><th>Project</th><th>History</th><th>Change</th><th>Trend</th></tr></thead>
          <tbody>{(data?.items ?? []).map((r) => (
            <tr key={r.project_id}>
              <td><strong>{r.project_name}</strong><span className="row-code">{r.project_code}</span></td>
              <td>
                {r.history.map((h, i) => (
                  <span key={i} style={{ display: "inline-flex", alignItems: "center" }}>
                    {i > 0 && <ArrowRight size={10} style={{ margin: "0 4px", color: "var(--ink-3)" }} />}
                    <span>{h.overall_score ?? "—"}</span>
                  </span>
                ))}
              </td>
              <td>
                <span style={{ fontWeight: 600, color: (r.score_change ?? 0) > 0 ? "var(--error)" : (r.score_change ?? 0) < 0 ? "var(--success)" : "inherit" }}>
                  {r.score_change === null ? "—" : `${r.score_change > 0 ? "+" : ""}${r.score_change}`}
                </span>
              </td>
              <td>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Link className="link" to={`/projects/${r.project_id}`} style={{ display: "inline-flex", alignItems: "center", gap: 3 }}>
                    View <ArrowRight size={12} />
                  </Link>
                  <span style={{ color: "var(--ink-3)" }}>·</span>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: "0.82rem", textTransform: "capitalize" }}>
                    {r.trend === "deteriorating" ? (
                      <TrendingDown size={14} color="var(--error)" />
                    ) : r.trend === "improving" ? (
                      <TrendingUp size={14} color="var(--success)" />
                    ) : (
                      <Minus size={14} color="var(--ink-3)" />
                    )}
                    {r.trend}
                  </span>
                </div>
              </td>
            </tr>
          ))}</tbody>
        </table></div></div>
      </div>
    </section>
  );
}
