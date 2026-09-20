import { useState } from "react";
import { Sliders, Play, ArrowRight, TrendingUp, TrendingDown } from "lucide-react";
import { API_URL, formatNumber } from "../api";

export default function SimulationPage(){
  const [projectId,setProjectId]=useState("1");
  const [progress,setProgress]=useState("");
  const [revised,setRevised]=useState("");
  const [result,setResult]=useState<any>(null);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(false);
  async function run(e:React.FormEvent){
    e.preventDefault(); setLoading(true); setError("");
    try{
      const body:any={ project_id: Number(projectId) };
      if(progress) body.physical_progress_pct=Number(progress);
      if(revised) body.revised_cost_cr=Number(revised);
      const res=await fetch(`${API_URL}/simulation/project`,{method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
      if(!res.ok) throw new Error(`Simulation failed (${res.status})`);
      setResult(await res.json());
    }catch(err){ setError(err instanceof Error?err.message:String(err)); } finally{ setLoading(false); }
  }
  return (
    <section className="section" aria-labelledby="t"><div className="wrap">
      <div className="section-head">
        <p className="section-eyebrow">Predictions · What-if Simulation</p>
        <h2 id="t" style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Sliders size={24} color="var(--navy-700)" /> Project Simulation (read-only, never persists)
        </h2>
        <p>Adjust progress or revised cost and see simulated risk. Heuristic adjustments, illustrative only.</p>
      </div>
      <form onSubmit={run} className="panel" style={{padding:16, display:"grid", gap:12, maxWidth:560}}>
        <div className="field"><span><label htmlFor="pid">Project ID</label></span><input id="pid" value={projectId} onChange={e=>setProjectId(e.target.value)} required/></div>
        <div className="field"><span><label htmlFor="prog">Simulated progress % (0-100)</label></span><input id="prog" type="number" min={0} max={100} value={progress} onChange={e=>setProgress(e.target.value)} placeholder="e.g. 85"/></div>
        <div className="field"><span><label htmlFor="rev">Simulated revised cost (cr)</label></span><input id="rev" type="number" min={0} value={revised} onChange={e=>setRevised(e.target.value)} placeholder="e.g. 2500"/></div>
        <button className="btn btn-primary" disabled={loading} style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
          <Play size={15} /> {loading?"Simulating…":"Run simulation"}
        </button>
      </form>
      {error && <div className="alert alert-error" style={{marginTop:12}}>{error}</div>}
      {result && (
        <div className="panel" style={{marginTop:12, padding:16}}>
          <h3 style={{color:"#0D3157", display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap"}}>
            {result.project_code} — {formatNumber(result.original_overall_score,1)} <ArrowRight size={15} /> {formatNumber(result.simulated_overall_score,1)}
            <span style={{color: (result.delta??0) >0 ? "#B42318":"#16803C", display: "inline-flex", alignItems: "center", gap: 2, marginLeft: 4}}>
              {result.delta!==null && (result.delta>0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />)}
              {result.delta!==null?`${result.delta>0?"+":""}${formatNumber(result.delta,1)}`:""}
            </span>
          </h3>
          <p style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {result.original_band} <ArrowRight size={13} /> {result.simulated_band}
          </p>
          <ul>{result.assumptions.map((a:string)=><li key={a} style={{fontSize:"0.85rem", color:"#52606D"}}>{a}</li>)}</ul>
          <p style={{fontSize:"0.78rem", color:"#6B7280"}}>{result.note}</p>
        </div>
      )}
    </div></section>
  );
}
