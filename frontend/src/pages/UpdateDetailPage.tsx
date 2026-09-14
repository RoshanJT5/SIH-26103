import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getJson } from "../api";

type UpdateItem = { id: number; category: string; title: string; summary: string; content: string; published_at: string; updated_at: string; status: string; related_dataset_id: number | null };

export default function UpdateDetailPage() {
  const { id } = useParams();
  const [item, setItem] = useState<UpdateItem | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!id) return;
    getJson<UpdateItem>(`/updates/${id}`).then(setItem).catch((e: Error) => setError(e.message)).finally(() => setLoading(false));
  }, [id]);
  if (loading) return <section className="section"><div className="wrap"><div className="panel loading" role="status"><span className="spinner" />Loading update…</div></div></section>;
  if (error) return <section className="section"><div className="wrap"><div className="alert alert-error" role="alert">Unable to load update. {error}</div><Link className="link" to="/updates">← Back to Updates</Link></div></section>;
  if (!item) return null;
  return (
    <section className="section">
      <div className="wrap">
        <p><Link className="link" to="/updates">← Back to Updates</Link></p>
        <span className="st" style={{ background: "#EFF4FB", borderColor: "#B9C9E4", color: "#0D3157" }}>{item.category}</span>
        <h1 style={{ color: "#0D3157", margin: "10px 0 6px" }}>{item.title}</h1>
        <p style={{ color: "#52606D", fontSize: "0.85rem" }}>{new Date(item.published_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })} · Updated {new Date(item.updated_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}</p>
        <p style={{ fontSize: "1.05rem", color: "#1D2939", fontWeight: 600 }}>{item.summary}</p>
        <div className="panel" style={{ padding: 20, marginTop: 16 }}><p style={{ whiteSpace: "pre-line", margin: 0 }}>{item.content}</p></div>
        {item.related_dataset_id && <p style={{ marginTop: 12 }}><Link className="link" to="/documents">View related dataset →</Link></p>}
      </div>
    </section>
  );
}
