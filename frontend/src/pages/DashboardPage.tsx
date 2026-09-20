import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { formatCrore, formatNumber, getJson, API_URL, type AssistantResponse, type Dashboard } from "../api";


export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState<AssistantResponse | null>(null);
  const [asking, setAsking] = useState(false);
  const [trends,setTrends]=useState<any>(null);
  const [priority,setPriority]=useState<any>(null);
  const [warnings,setWarnings]=useState<any>(null);
  const [drivers,setDrivers]=useState<any>(null);

  useEffect(() => {
    getJson<Dashboard>("/dashboard/summary").then(setDashboard).catch((e: Error) => setError(e.message)).finally(() => setLoading(false));
    getJson<any>("/risk/trends?limit=5").then(setTrends).catch(()=>null);
    getJson<any>("/interventions/priority?limit=5").then(setPriority).catch(()=>null);
    getJson<any>("/early-warnings?limit=5").then(setWarnings).catch(()=>null);
    getJson<any>("/analytics/cost-drivers?limit=5").then(setDrivers).catch(()=>null);
  }, []);

  async function ask(e: FormEvent) {
    e.preventDefault(); if (!q.trim()) return; setAsking(true);
    try { const res = await fetch(`${API_URL}/assistant/query`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q }) }); if (!res.ok) throw new Error(`Assistant request failed (${res.status})`); setAnswer(await res.json()); } catch (err) { setAnswer({ answer: err instanceof Error ? err.message : "Assistant unavailable.", intent: "unknown", sources: [], provider_status: "disabled", caveats: [] }); } finally { setAsking(false); }

  }

  return (
    <section className="section" aria-labelledby="t"><div className="wrap">
      <div className="section-head"><p className="section-eyebrow">Monitoring · Dashboard — 10-block portfolio</p><h2 id="t">Portfolio risk dashboard</h2><p>Live from /dashboard/summary and six supporting endpoints. All blocks read live backend.</p></div>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {loading ? <div className="panel loading" role="status"><span className="spinner" />Loading summary…</div> : dashboard && (
        <>
          <div className="card-grid" style={{marginBottom:16}}>
            <article className="card"><h3>1 · Projects tracked</h3><p style={{fontSize:"1.8rem",fontWeight:700,color:"#123B73"}}>{formatNumber(dashboard.total_projects)}</p><p>{formatNumber(dashboard.available_predictions)} with stored scores</p><Link className="link" to="/projects">View projects →</Link></article>
            <article className="card"><h3>2 · High / Critical</h3><p style={{fontSize:"1.8rem",fontWeight:700,color:"#123B73"}}>{dashboard.high_risk_projects} / {dashboard.critical_projects}</p><p>Average {formatNumber(dashboard.average_overall_score,1)} /100</p><Link className="link" to="/analytics">See analytics →</Link></article>
            <article className="card"><h3>3 · Capital reported</h3><p style={{fontSize:"1.4rem",fontWeight:700,color:"#123B73"}}>{formatCrore(dashboard.total_revised_cost_cr || dashboard.total_original_cost_cr)}</p><p>Expenditure {formatCrore(dashboard.total_expenditure_cr)}</p></article>
          </div>
          <div className="panel" style={{marginBottom:16}}><div className="panel-head"><div><p className="section-eyebrow">4 · Dataset</p><h3>Current snapshot</h3></div></div><div style={{padding:16}}><div className="fact-grid"><div><span>Source file</span><strong>{dashboard.dataset?.source_name ?? "None"}</strong></div><div><span>Source date</span><strong>{dashboard.dataset?.source_as_of_date ?? "Unavailable"}</strong></div><div><span>Imported at</span><strong>{dashboard.dataset?.imported_at ?? "—"}</strong></div><div><span>Dataset ID</span><strong>{dashboard.dataset ? String(dashboard.dataset.dataset_id) : "—"}</strong></div></div></div></div>

          <div className="card-grid" style={{marginBottom:16}}>
            <article className="card"><h3>5 · Early warnings</h3><p>{warnings ? `${warnings.items?.length ?? 0} open signals` : "Loading…"}</p><ul style={{fontSize:"0.8rem", margin:"6px 0"}}>{warnings?.items?.slice(0,3).map((w:any)=><li key={w.id}>{w.type} — {w.severity}</li>)}</ul><Link className="link" to="/early-warnings">Open warning center →</Link></article>
            <article className="card"><h3>6 · Priority queue</h3><p>{priority ? `Top priority ${priority.items?.[0]?.project_code ?? "—"}` : "Loading…"}</p><p style={{fontSize:"0.8rem"}}>{priority?.formula?.slice(0,60) ?? ""}</p><Link className="link" to="/interventions">View queue →</Link></article>
            <article className="card"><h3>7 · Deteriorating trends</h3><p>{trends ? `${trends.items?.filter((t:any)=>t.trend!=="stable").length ?? 0} worsening` : "Loading…"}</p><p style={{fontSize:"0.8rem"}}>Thresholds: watch/deteriorating/rapid</p><Link className="link" to="/monitoring/changes">Check changes →</Link></article>
          </div>

          <div className="card-grid" style={{marginBottom:16}}>
            <article className="card"><h3>8 · Sector pulse</h3><Link className="link" to="/analytics">Sector analytics →</Link><p style={{fontSize:"0.8rem"}}>Per-sector average risk and counts</p></article>
            <article className="card"><h3>9 · Cost drivers</h3>{drivers ? <ul style={{fontSize:"0.8rem"}}>{drivers.items?.slice(0,3).map((d:any)=><li key={d.feature}>{d.feature}: {formatNumber(d.average_shap,3)}</li>)}</ul> : <p>Loading…</p>}<Link className="link" to="/analytics">Explore drivers →</Link></article>
            <article className="card"><h3>10 · Simulation</h3><p style={{fontSize:"0.85rem"}}>What-if progress or cost adjustments — read-only, never persists.</p><Link className="link" to="/simulation">Try simulation →</Link></article>
          </div>

          <div className="panel" style={{marginBottom:16}}><div className="panel-head"><div><p className="section-eyebrow">Priority snapshot (chart)</p><h3>Top priority scores</h3></div></div><div style={{padding:"6px 14px 14px"}}>{priority && <ResponsiveContainer width="100%" height={180}><BarChart data={priority.items.slice(0,6).map((i:any)=>({name:i.project_code, score:i.priority_score}))}><CartesianGrid stroke="#D9E1EA"/><XAxis dataKey="name" tick={{fontSize:10}}/><YAxis domain={[0,100]} tick={{fontSize:11}}/><Tooltip/><Bar dataKey="score" fill="#164A7A"/></BarChart></ResponsiveContainer>}</div></div>
        </>
      )}
      <section className="panel" id="assistant" style={{ marginTop: 16 }} aria-labelledby="a"><div className="panel-head"><div><p className="section-eyebrow">Grounded assistant</p><h3 id="a">Ask the portfolio — POST /assistant/query</h3></div></div><div style={{ padding: 16 }}><p style={{fontSize:"0.8rem", color:"#52606D"}}>New intents: find_deteriorating_projects, list_early_warnings, show_priority, show_cost_drivers.</p><form className="assistant-form" onSubmit={ask} role="search"><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Try: find deteriorating projects" aria-label="Ask the portfolio assistant" /><button className="btn btn-primary" disabled={asking}>{asking ? "Thinking…" : "Ask"}</button></form>{answer && <div className="assistant-answer" role="status"><p>{answer.answer}</p><div className="assistant-meta"><span>{answer.provider_status}</span><span>{answer.sources.length} sources</span><span>{answer.intent}</span></div>{answer.caveats.map((c) => <small key={c} style={{ display: "block" }}>{c}</small>)}</div>}</div></section>
    </div></section>
  );
}
