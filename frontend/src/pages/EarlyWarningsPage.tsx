import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getJson, Band } from "../api";

type EW = { id:number; project_id:number; type:string; severity:string; title:string; description:string; status:string; project_code:string|null; project_name:string|null};

export default function EarlyWarningsPage(){
  const [items,setItems]=useState<EW[]>([]);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [filter,setFilter]=useState("");
  useEffect(()=>{ getJson<{items:EW[]}>("/early-warnings?limit=100").then(r=>setItems(r.items)).catch((e:Error)=>setError(e.message)).finally(()=>setLoading(false));},[]);
  const filtered = filter ? items.filter(i=>i.severity===filter) : items;
  if(loading) return <section className="section"><div className="wrap"><div className="panel loading" role="status"><span className="spinner"/>Loading warnings…</div></div></section>;
  if(error) return <section className="section"><div className="wrap"><div className="alert alert-error" role="alert">{error}</div></div></section>;
  if(items.length===0) return <section className="section"><div className="wrap"><div className="section-head"><p className="section-eyebrow">Monitoring</p><h2>Early Warnings</h2><p>No early warnings in this snapshot. Warnings generate deterministically on risk escalation, progress deviation and cost escalation.</p></div><div className="panel" style={{padding:24}}><p>No warnings — all projects stable.</p></div></div></section>;
  return (
    <section className="section" aria-labelledby="t"><div className="wrap">
      <div className="section-head"><p className="section-eyebrow">Monitoring · Early Warning Center</p><h2 id="t">Early Warnings</h2><p>Deterministic signals: risk_escalation, progress_deviation, cost_escalation, schedule_slippage, rapid_deterioration, expenditure_deviation. Status: open / acknowledged / closed (admin).</p></div>
      <div className="filters" role="search"><div className="field"><span><label htmlFor="sev">Severity</label></span><select id="sev" value={filter} onChange={e=>setFilter(e.target.value)}><option value="">All</option><option value="watch">Watch</option><option value="high">High</option><option value="critical">Critical</option></select></div></div>
      <div className="panel"><div className="table-wrap"><table className="gov-table"><thead><tr><th>Project</th><th>Type</th><th>Severity</th><th>Title</th><th>Status</th><th>Action</th></tr></thead><tbody>{filtered.map(w=> <tr key={w.id}><td><strong>{w.project_name ?? w.project_code ?? `#${w.project_id}`}</strong><span className="row-code">{w.project_code}</span></td><td>{w.type}</td><td><Band band={w.severity==="watch"?"medium":w.severity}/></td><td>{w.title}</td><td>{w.status}</td><td><Link className="link" to={`/projects/${w.project_id}`}>View →</Link></td></tr>)}</tbody></table></div></div>
    </div></section>
  );
}
