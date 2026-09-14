import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { getJson, formatNumber } from "../api";

export default function InterventionsPage(){
  const [data,setData]=useState<{items:any[]; formula:string; version:string}|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  useEffect(()=>{ getJson<any>("/interventions/priority?limit=50").then(setData).catch((e:Error)=>setError(e.message)).finally(()=>setLoading(false));},[]);
  if(loading) return <section className="section"><div className="wrap"><div className="panel loading"><span className="spinner"/>Loading priority queue…</div></div></section>;
  if(error) return <section className="section"><div className="wrap"><div className="alert alert-error">{error}</div></div></section>;
  if(!data || data.items.length===0) return <section className="section"><div className="wrap"><div className="panel" style={{padding:24}}>No scored projects for prioritization.</div></div></section>;
  const chart=data.items.slice(0,12).map((i:any)=>({ name:i.project_code, score: i.priority_score }));
  return (
    <section className="section" aria-labelledby="t"><div className="wrap">
      <div className="section-head"><p className="section-eyebrow">Predictions · Intervention Priority</p><h2 id="t">Priority Queue</h2><p>Transparent weighted score: {data.formula}. Version {data.version}. Drivers list per project shows contributions.</p></div>
      <div className="panel" style={{marginBottom:16}}><div style={{padding:"6px 14px 14px"}}><h3 style={{color:"#0D3157"}}>Priority scores (top 12)</h3><ResponsiveContainer width="100%" height={260}><BarChart data={chart} layout="vertical" margin={{left:12,right:12}}><CartesianGrid stroke="#D9E1EA" horizontal={false}/><XAxis type="number" domain={[0,100]} hide/><YAxis type="category" dataKey="name" width={110} tick={{fontSize:11}}/><Tooltip formatter={(v)=>`${formatNumber(Number(v),1)} /100`}/><Bar dataKey="score" fill="#164A7A" radius={[0,4,4,0]} barSize={16}/></BarChart></ResponsiveContainer><table className="gov-table"><caption style={{textAlign:"left",color:"#52606D"}}>Text alternative — priority_score /100. Source: stored predictions.</caption><thead><tr><th>Rank</th><th>Project</th><th>Score</th><th>Band</th></tr></thead><tbody>{data.items.slice(0,12).map((i:any)=><tr key={i.project_id}><td>{i.rank}</td><td>{i.project_code}</td><td>{formatNumber(i.priority_score,1)}</td><td>{i.risk_band??"—"}</td></tr>)}</tbody></table></div></div>
      <div className="panel"><div className="table-wrap"><table className="gov-table"><thead><tr><th>Rank</th><th>Project</th><th>Sector</th><th>Priority</th><th>Drivers</th><th>Action</th></tr></thead><tbody>{data.items.map((i:any)=><tr key={i.project_id}><td>{i.rank}</td><td><strong>{i.project_name}</strong><span className="row-code">{i.project_code}</span></td><td>{i.sector}</td><td>{formatNumber(i.priority_score,1)}</td><td style={{fontSize:"0.75rem"}}>{i.drivers.slice(0,3).map((d:any)=>`${d.factor}:${formatNumber(d.contribution,1)}`).join(" · ")}</td><td><Link className="link" to={`/projects/${i.project_id}`}>View →</Link></td></tr>)}</tbody></table></div></div>
    </div></section>
  );
}
