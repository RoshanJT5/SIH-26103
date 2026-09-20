import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { getJson } from "../api";

type UpdateItem = { id: number; category: string; title: string; summary: string; content: string; published_at: string; updated_at: string; status: string; related_dataset_id: number | null };
type ListResp = { items: UpdateItem[]; total: number; limit: number; offset: number };

const CATS = ["All", "dataset", "monitoring", "model", "methodology", "platform"] as const;

function badgeColor(cat: string) {
  if (cat === "dataset") return { bg: "#EFFAF2", border: "#BFE3CC", color: "#14662E" };
  if (cat === "monitoring") return { bg: "#FFF4EA", border: "#F5C6A8", color: "#9C4221" };
  if (cat === "model") return { bg: "#EFF4FB", border: "#B9C9E4", color: "#0D3157" };
  if (cat === "methodology") return { bg: "#FFF7E8", border: "#F0D9A8", color: "#8A5A00" };
  return { bg: "#F3F7FB", border: "#D9E1EA", color: "#164A7A" };
}

function fmtDate(s: string) {
  return new Date(s).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export default function UpdatesPage() {
  const [params, setParams] = useSearchParams();
  const cat = params.get("category") ?? "All";
  const search = params.get("search") ?? "";
  const [q, setQ] = useState(search);
  const [data, setData] = useState<ListResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => { setQ(search); }, [search]);

  useEffect(() => {
    setLoading(true);
    setError("");
    const qs = new URLSearchParams();
    if (cat !== "All") qs.set("category", cat);
    if (search) qs.set("search", search);
    qs.set("limit", "20");
    getJson<ListResp>(`/updates?${qs.toString()}`).then(setData).catch((e: Error) => setError(e.message)).finally(() => setLoading(false));
  }, [cat, search]);

  function applySearch() {
    const next = new URLSearchParams(params);
    if (q) next.set("search", q); else next.delete("search");
    setParams(next);
  }

  const featured = data?.items[0] ?? null;
  const rest = data ? data.items.slice(1) : [];

  return (
    <section className="section">
      <div className="wrap">
        <div className="section-head">
          <p className="section-eyebrow">Updates</p>
          <h1 style={{ margin: 0, fontSize: "clamp(1.6rem, 3vw, 2.2rem)", color: "#0D3157" }}>Latest Updates</h1>
          <p>Official project monitoring, dataset, methodology and platform updates. For demonstration only — not official Government of India announcements.</p>
        </div>

        <div className="filters" role="search" aria-label="Filter updates">
          <div className="field search-field"><span><label htmlFor="uq">Search</label></span><input id="uq" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") applySearch(); }} placeholder="Search title or summary" /></div>
          <button className="btn btn-secondary btn-sm" type="button" onClick={applySearch}>Search</button>
          <div className="field"><span>Category</span>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {CATS.map((c) => (
                <button key={c} type="button" className={`btn btn-sm ${cat === c ? "btn-primary" : "btn-secondary"}`} onClick={() => { const n = new URLSearchParams(params); if (c === "All") n.delete("category"); else n.set("category", c); setParams(n); }}>{c}</button>
              ))}
            </div>
          </div>
        </div>

        {loading && <div className="panel loading" role="status"><span className="spinner" />Loading latest updates…</div>}
        {error && <div className="alert alert-error" role="alert">Unable to load updates. {error} <button className="btn btn-secondary btn-sm" type="button" onClick={() => window.location.reload()} style={{ marginLeft: 8 }}>Retry</button></div>}
        {!loading && !error && data && data.items.length === 0 && <div className="panel" style={{ padding: 24 }}>No updates are available for the selected filters.</div>}

        {!loading && !error && featured && (
          <article className="panel" style={{ borderLeft: "4px solid #F39A24", padding: 20, marginBottom: 16 }}>
            <span className="st" style={badgeColor(featured.category) as never}>{featured.category}</span>
            <p style={{ margin: "8px 0 4px", fontSize: "0.78rem", fontWeight: 700, color: "#52606D" }}>{fmtDate(featured.published_at)}</p>
            <h2 style={{ margin: "4px 0", color: "#0D3157" }}>{featured.title}</h2>
            <p style={{ color: "#52606D" }}>{featured.summary}</p>
            <Link className="link" to={`/updates/${featured.id}`} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>View Details <ArrowRight size={13} /></Link>
          </article>
        )}

        {!loading && !error && rest.length > 0 && (
          <ul className="upd" style={{ marginTop: 8 }}>
            {rest.map((u) => {
              const bc = badgeColor(u.category);
              return (
                <li key={u.id} className={u.category === "model" ? "m-saffron" : u.category === "dataset" ? "m-teal" : ""} style={{ background: "#fff", border: "1px solid #D9E1EA", borderLeft: `3px solid ${bc.border}`, borderRadius: 6, padding: "14px 16px", marginBottom: 10, marginLeft: 0 }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}><span className="st" style={bc as never}>{u.category}</span><time style={{ fontSize: "0.78rem", color: "#52606D" }}>{fmtDate(u.published_at)}</time></div>
                  <h3 style={{ margin: "6px 0 4px", color: "#0D3157", fontSize: "1.02rem" }}>{u.title}</h3>
                  <p style={{ margin: 0, color: "#52606D", fontSize: "0.9rem" }}>{u.summary}</p>
                  <Link className="link" to={`/updates/${u.id}`}>View Details</Link>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
