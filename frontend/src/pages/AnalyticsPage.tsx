import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { bandColors, formatNumber, getJson, type Group } from "../api";

export default function AnalyticsPage() {
  const [sectors, setSectors] = useState<Group[]>([]);
  const [ministries, setMinistries] = useState<Group[]>([]);
  const [drivers,setDrivers]=useState<any>(null);
  const [geo,setGeo]=useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getJson<Group[]>("/analytics/sectors"), getJson<Group[]>("/analytics/ministries"), getJson<any>("/analytics/cost-drivers").catch(()=>null), getJson<any>("/analytics/geography").catch(()=>null)])
      .then(([s, m, d, g]) => { setSectors(s); setMinistries(m); setDrivers(d); setGeo(g); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="section" aria-labelledby="t">
      <div className="wrap">
        <div className="section-head"><p className="section-eyebrow">Analytics</p><h2 id="t">Sector and ministry analytics</h2><p>Live from <code>GET /analytics/sectors</code> and <code>GET /analytics/ministries</code>. Charts include text alternatives and sources.</p></div>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        {loading ? <div className="panel loading" role="status"><span className="spinner" />Loading analytics…</div> : (
          <>
            <div className="panel" style={{ marginBottom: 16 }}>
              <div className="panel-head"><div><p className="section-eyebrow">Sector pulse</p><h3>Average risk by sector</h3></div></div>
              <div style={{ padding: "6px 14px 14px" }}>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={sectors.slice(0, 10)} layout="vertical" margin={{ top: 4, right: 12, bottom: 4, left: 12 }}>
                    <CartesianGrid horizontal={false} stroke="#D9E1EA" />
                    <XAxis type="number" domain={[0, 100]} hide />
                    <YAxis type="category" dataKey="group" width={120} tick={{ fontSize: 12 }} />
                    <Tooltip formatter={(v) => `${formatNumber(Number(v), 1)} / 100`} />
                    <Bar dataKey="average_overall_score" fill="#1F5AA6" radius={[0, 4, 4, 0]} barSize={18}>
                      {sectors.slice(0, 10).map((s) => <Cell key={s.group} fill={s.average_overall_score && s.average_overall_score > 60 ? "#C53030" : "#1F5AA6"} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div className="table-wrap"><table className="gov-table">
                  <caption style={{ textAlign: "left", padding: "6px 0", color: "#4B5563" }}>Text alternative — units: score / 100. Source: stored model results.</caption>
                  <thead><tr><th scope="col">Sector</th><th scope="col">Projects</th><th scope="col">Avg score</th><th scope="col">High</th><th scope="col">Critical</th></tr></thead>
                  <tbody>{sectors.map((s) => <tr key={s.group}><td><strong>{s.group}</strong></td><td>{formatNumber(s.project_count)}</td><td>{formatNumber(s.average_overall_score, 1)}</td><td>{formatNumber(s.high_risk_projects)}</td><td>{formatNumber(s.critical_projects)}</td></tr>)}</tbody>
                </table></div>
              </div>
            </div>
            <div className="panel" style={{marginBottom:16}}>
              <div className="panel-head"><div><p className="section-eyebrow">Ministry view</p><h3>Average risk by ministry</h3></div></div>
              <div style={{ padding: "6px 14px 14px" }}>
                <ResponsiveContainer width="100%" height={260}>
                  <ScatterChart margin={{ top: 10, right: 12, bottom: 8, left: -10 }}>
                    <CartesianGrid stroke="#D9E1EA" strokeDasharray="3 3" />
                    <XAxis type="number" dataKey="x" name="Projects" tick={{ fontSize: 11 }} />
                    <YAxis type="number" dataKey="y" name="Avg score" domain={[0, 100]} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v) => formatNumber(Number(v), 1)} />
                    <Scatter data={ministries.map((m) => ({ x: m.project_count, y: m.average_overall_score ?? 0, name: m.group }))} fill="#174A8B">
                      {ministries.map((m) => <Cell key={m.group} fill={bandColors[m.high_risk_projects > m.critical_projects ? "high" : "low"] ?? "#174A8B"} />)}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
                <div className="table-wrap"><table className="gov-table">
                  <thead><tr><th scope="col">Ministry</th><th scope="col">Projects</th><th scope="col">Avg score</th></tr></thead>
                  <tbody>{ministries.slice(0, 10).map((m) => <tr key={m.group}><td><strong>{m.group}</strong></td><td>{formatNumber(m.project_count)}</td><td>{formatNumber(m.average_overall_score, 1)}</td></tr>)}</tbody>
                </table></div>
              </div>
            </div>
            <div className="panel" style={{marginBottom:16}}><div className="panel-head"><div><p className="section-eyebrow">Cost drivers</p><h3>Average SHAP by feature</h3></div></div><div style={{padding:"6px 14px 14px"}}>{drivers ? <><ResponsiveContainer width="100%" height={240}><BarChart data={drivers.items.slice(0,8)} layout="vertical" margin={{left:12}}><CartesianGrid horizontal={false} stroke="#D9E1EA"/><XAxis type="number" hide/><YAxis type="category" dataKey="feature" width={120} tick={{fontSize:11}}/><Tooltip formatter={(v)=>formatNumber(Number(v),4)}/><Bar dataKey="average_shap" fill="#1F5AA6" radius={[0,4,4,0]} /></BarChart></ResponsiveContainer><div className="table-wrap"><table className="gov-table"><caption style={{textAlign:"left", color:"#6B7280"}}>Text alternative — average SHAP units. Source: stored explanations.</caption><thead><tr><th>Feature</th><th>Avg SHAP</th><th>Coverage</th></tr></thead><tbody>{drivers.items.slice(0,8).map((d:any)=><tr key={d.feature}><td>{d.feature}</td><td>{formatNumber(d.average_shap,4)}</td><td>{d.coverage}</td></tr>)}</tbody></table></div></> : <p>Loading drivers…</p>}</div></div>
            <div className="panel"><div className="panel-head"><div><p className="section-eyebrow">Geography (illustrative)</p><h3>Region aggregates</h3></div></div><div style={{padding:"6px 14px 14px"}}>{geo ? <><div className="map-panel" style={{border:"1px solid #D9E1EA", borderRadius:6, padding:12, background:"#F7F9FC"}}><p style={{fontSize:"0.8rem", color:"#52606D"}}>{geo.note} · {geo.methodology}</p><div style={{display:"grid", gridTemplateColumns:"repeat(2,1fr)", gap:8, marginTop:8}}>{geo.regions.slice(0,8).map((g:any)=><div key={g.region} style={{border:"1px solid #D9E1EA", padding:8, borderRadius:4, background:"#fff"}}><strong style={{fontSize:"0.8rem"}}>{g.region}</strong><br/><span style={{fontSize:"0.75rem", color:"#52606D"}}>{formatNumber(g.project_count)} projects · avg {formatNumber(g.average_overall_score,1)}</span></div>)}</div></div><div className="table-wrap" style={{marginTop:8}}><table className="gov-table"><thead><tr><th>Region</th><th>Projects</th><th>Avg score</th><th>High</th></tr></thead><tbody>{geo.regions.map((g:any)=><tr key={g.region}><td>{g.region}</td><td>{formatNumber(g.project_count)}</td><td>{formatNumber(g.average_overall_score,1)}</td><td>{formatNumber(g.high_risk_projects)}</td></tr>)}</tbody></table></div></> : <p>Loading geography…</p>}</div></div>
          </>
        )}
      </div>
    </section>
  );
}
