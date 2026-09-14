import { useEffect, useState } from "react";
import { getJson } from "../api";

export default function ModelsPage(){
  const [models,setModels]=useState<any[]>([]);
  const [perf,setPerf]=useState<any>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  useEffect(()=>{
    Promise.all([getJson<{items:any[]}>("/ml/models").catch(()=>({items:[]})), getJson<any>("/ml/performance").catch(()=>null)]).then(([m,p])=>{ setModels(m.items); setPerf(p); }).catch((e:Error)=>setError(e.message)).finally(()=>setLoading(false));
  },[]);
  if(loading) return <section className="section"><div className="wrap"><div className="panel loading"><span className="spinner"/>Loading models…</div></div></section>;
  return (
    <section className="section" aria-labelledby="t"><div className="wrap">
      <div className="section-head"><p className="section-eyebrow">Analytics · ML Models</p><h2 id="t">Model Registry & Performance</h2><p>Stored model versions and held-out metrics. Use <code>GET /ml/models</code> and <code>GET /ml/performance</code>.</p></div>
      {error && <div className="alert alert-error">{error}</div>}
      {perf && <div className="panel" style={{padding:16, marginBottom:16}}><h3>Performance — {perf.target_type}</h3><pre style={{fontSize:"0.8rem", overflow:"auto"}}>{JSON.stringify(perf.latest_metrics, null, 2)}</pre><p style={{fontSize:"0.78rem", color:"#52606D"}}>{perf.note}</p></div>}
      {models.length===0 ? <div className="panel" style={{padding:24}}><p>No trained models yet. Run <code>python -m ml.training.train --dataset-id N</code>.</p></div> : (
        <div className="panel"><div className="table-wrap"><table className="gov-table"><thead><tr><th>ID</th><th>Name</th><th>Target</th><th>Created</th><th>Metrics</th></tr></thead><tbody>{models.map((m:any)=><tr key={m.id}><td>{m.id}</td><td>{m.name}</td><td>{m.target_type}</td><td>{String(m.created_at).slice(0,19)}</td><td style={{fontSize:"0.75rem"}}>{JSON.stringify(m.metrics).slice(0,120)}</td></tr>)}</tbody></table></div></div>
      )}
    </div></section>
  );
}
