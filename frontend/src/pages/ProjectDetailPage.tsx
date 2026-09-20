import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from "recharts";
import { ArrowLeft, ArrowRight, FileText } from "lucide-react";
import { Band, formatCrore, formatNumber, formatPercent, getJson, postJson, type Benchmark, type Detail, type Explanation } from "../api";

export default function ProjectDetailPage() {
  const { id } = useParams();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null);
  const [explanations, setExplanations] = useState<Explanation[]>([]);
  const [confidence,setConfidence]=useState<any>(null);
  const [trajectory,setTrajectory]=useState<any>(null);
  const [forecast,setForecast]=useState<any>(null);
  const [recs,setRecs]=useState<any>(null);
  const [timeline,setTimeline]=useState<any>(null);
  const [priority,setPriority]=useState<any>(null);
  const [early,setEarly]=useState<any>(null);
  const [report,setReport]=useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return; setLoading(true);
    Promise.all([
      getJson<Detail>(`/risk/projects/${id}`),
      getJson<Benchmark>(`/analytics/benchmarks?project_id=${id}`),
      getJson<{ explanations: Explanation[] }>(`/risk/projects/${id}/explanation`).catch(() => ({ explanations: [] })),
      getJson<any>(`/risk/projects/${id}/confidence`).catch(()=>null),
      getJson<any>(`/projects/${id}/progress-trajectory`).catch(()=>null),
      getJson<any>(`/risk/projects/${id}/forecast`).catch(()=>null),
      getJson<any>(`/projects/${id}/recommendations`).catch(()=>null),
      getJson<any>(`/projects/${id}/timeline`).catch(()=>null),
      getJson<any>(`/interventions/priority/${id}`).catch(()=>null),
      getJson<any>(`/early-warnings?project_id=${id}&limit=5`).catch(()=>null),
    ]).then(([d, b, e, c, t, f, r, tl, p, ew]) => { setDetail(d); setBenchmark(b); setExplanations(e.explanations); setConfidence(c); setTrajectory(t); setForecast(f); setRecs(r); setTimeline(tl); setPriority(p); setEarly(ew); }).catch((err: Error) => setError(err.message)).finally(() => setLoading(false));
  }, [id]);

  async function genReport(){
    try{ const r=await postJson<any>("/reports/project-brief",{project_id:Number(id)}); setReport(r); }catch(e){ setReport({error: e instanceof Error?e.message:"Failed"}); }
  }

  return (
    <section className="section" aria-labelledby="t"><div className="wrap">
      <p>
        <Link className="link" to="/projects" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
          <ArrowLeft size={14} /> Back to Projects
        </Link>
      </p>
      <div className="section-head"><p className="section-eyebrow">Project detail — 13-section investigation</p><h2 id="t">Investigation · {detail?.project_code ?? `#${id}`}</h2><p>Sections: facts, risk, confidence, trajectory, forecast, recommendations, drivers, benchmark, timeline, priority, warnings, limitations, report.</p></div>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {loading ? <div className="panel loading" role="status"><span className="spinner" />Loading project…</div> : detail && (
        <>
          <div className="panel" style={{ padding: 18 }}>
            <h3 style={{ margin: "0 0 4px", color: "#123B73" }}>1 · Project Facts — {detail.project_name}</h3>
            <p style={{ margin: 0, color: "#4B5563" }}>{detail.sector} / {detail.ministry} · {detail.implementing_agency}</p>
            <p style={{ marginTop: 8 }}><Band band={detail.risk_band} /> <strong style={{ marginLeft: 8 }}>{detail.overall_score === null ? "—" : formatNumber(detail.overall_score)} / 100</strong></p>
            <div className="fact-grid">
              <div><span>2 · Original cost</span><strong>{formatCrore(detail.original_cost_cr)}</strong></div>
              <div><span>Revised cost</span><strong>{formatCrore(detail.revised_cost_cr)}</strong></div>
              <div><span>Expenditure</span><strong>{formatCrore(detail.expenditure_cr)}</strong></div>
              <div><span>Progress</span><strong>{formatPercent(detail.physical_progress_pct)}</strong></div>
              <div><span>Cost escalation</span><strong>{formatPercent(detail.cost_escalation_pct)}</strong></div>
              <div><span>Schedule revision</span><strong>{detail.schedule_revision_days === null ? "Unavailable" : `${formatNumber(detail.schedule_revision_days)} days`}</strong></div>
            </div>
          </div>

          <div className="card-grid" style={{marginTop:16}}>
            <article className="card"><h3>3 · Confidence & Data Quality</h3>{confidence ? <><p>Quality {confidence.data_quality} ({formatNumber(confidence.data_quality_score,1)}/100)</p><p style={{fontSize:"0.8rem"}}>Confidence {formatNumber(confidence.confidence,3)} · Prob {formatNumber(confidence.probability,3)}</p><p style={{fontSize:"0.75rem",color:"#6B7280"}}>{confidence.limitations?.slice(0,1).join(" ")}</p></> : <p>Unavailable</p>}</article>
            <article className="card"><h3>4 · Peer Benchmark</h3>{benchmark ? <p>Cohort {formatNumber(benchmark.cohort_size)} · Percentile {benchmark.percentile ?? "unavailable"} · Avg escalation {formatPercent(benchmark.average_cost_escalation_pct)}</p> : <p>No benchmark.</p>}<h3 style={{marginTop:8}}>10 · Priority</h3>{priority? <p>Rank #{priority.rank} · Score {formatNumber(priority.priority_score,1)}</p> : <p>—</p>}</article>
            <article className="card"><h3>5 · SHAP Drivers</h3>{explanations.length===0? <p>No stored explanations.</p>: explanations.slice(0,4).map((x)=><p key={x.feature_name} style={{fontSize:"0.85rem"}}>{x.feature_name}: <strong style={{color: x.shap_contribution>=0?"#C53030":"#16803C"}}>{formatNumber(x.shap_contribution,3)}</strong></p>)}<h3 style={{marginTop:8}}>12 · Limitations</h3><p style={{fontSize:"0.75rem"}}>Snapshot prototype; missing fields unavailable.</p></article>
          </div>

          <div className="card" style={{marginTop:16}}><h3>6 · Progress Trajectory (expected vs actual)</h3>{trajectory ? (trajectory.unavailable_reason ? <p>{trajectory.unavailable_reason}</p> : <ResponsiveContainer width="100%" height={200}><LineChart data={trajectory.points}><CartesianGrid stroke="#D9E1EA" strokeDasharray="3 3"/><XAxis dataKey="dataset_id" tick={{fontSize:11}}/><YAxis domain={[0,100]} tick={{fontSize:11}}/><Tooltip/><Legend/><Line type="monotone" dataKey="actual_progress" stroke="#164A7A" name="Actual" dot={{r:4}}/><Line type="monotone" dataKey="expected_progress" stroke="#C98A2E" strokeDasharray="5 5" name="Expected"/></LineChart></ResponsiveContainer>) : <p>Loading…</p>}<p style={{fontSize:"0.78rem", color:"#52606D"}}>Units: progress % · Source: snapshots · Method: expected=age/planned*100</p></div>

          <div className="card" style={{marginTop:16}}><h3>7 · Forecast (historical + dashed)</h3>{forecast ? <><ResponsiveContainer width="100%" height={200}><LineChart data={forecast.points}><CartesianGrid stroke="#D9E1EA" strokeDasharray="3 3"/><XAxis dataKey="dataset_id" tick={{fontSize:11}}/><YAxis domain={[0,100]} tick={{fontSize:11}}/><Tooltip/><Line dataKey="overall_score" stroke="#164A7A" dot={{fill:"#F39A24",r:4}} isAnimationActive={false} /><Line dataKey="overall_score" stroke="#C53030" strokeDasharray="6 4" dot={false} /></LineChart></ResponsiveContainer><p style={{fontSize:"0.75rem", color:"#52606D"}}>{forecast.methodology} · Limitations: {forecast.limitations?.join(" ")}</p></> : <p>Loading…</p>}</div>

          <div className="card-grid" style={{marginTop:16}}>
            <article className="card"><h3>8 · Recommendations (1-5 actions)</h3>{recs ? recs.items.map((r:any)=><p key={r.priority} style={{fontSize:"0.85rem"}}><strong>{r.priority}. {r.action}</strong><br/><span style={{color:"#6B7280"}}>{r.evidence} — {r.rationale}</span></p>) : <p>—</p>}</article>
            <article className="card">
              <h3>9 · Timeline</h3>
              {timeline ? timeline.points.slice(0,5).map((p:any)=><p key={p.snapshot_id} style={{fontSize:"0.8rem"}}>DS {p.dataset_id} — score {formatNumber(p.overall_score,1)} · {p.risk_band??"—"} · {formatPercent(p.physical_progress_pct)}</p>) : <p>—</p>}
              <Link className="link" to="/analytics" style={{ display: "inline-flex", alignItems: "center", gap: 3 }}>
                View analytics <ArrowRight size={13} />
              </Link>
            </article>
            <article className="card"><h3>11 · Early Warnings</h3>{early?.items?.length? early.items.map((w:any)=><p key={w.id} style={{fontSize:"0.8rem"}}><Band band={w.severity==="watch"?"medium":w.severity}/> {w.type}: {w.title}</p>) : <p>No open warnings for this project.</p>}</article>
          </div>

          <div className="card" style={{marginTop:16}}>
            <h3>13 · Project Brief Report</h3>
            <p style={{fontSize:"0.85rem"}}>Structured report with all required sections.</p>
            <button className="btn btn-secondary" onClick={genReport} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <FileText size={15} /> Generate Report
            </button>
            {report && <div style={{marginTop:12, padding:12, background:"#F7F9FC", borderRadius:6}}>{report.error ? <p>{report.error}</p> : report.sections?.map((s:any)=><div key={s.title} style={{marginBottom:8}}><strong>{s.title}</strong><p style={{fontSize:"0.85rem", margin:"2px 0"}}>{s.body.slice(0,220)}</p></div>)}</div>}
          </div>
        </>
      )}
    </div></section>
  );
}
