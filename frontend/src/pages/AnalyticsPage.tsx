import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { Band, bandColors, formatNumber, formatPercent, getJson, type Group, type Project } from "../api";

export default function AnalyticsPage() {
  const [sectors, setSectors] = useState<Group[]>([]);
  const [ministries, setMinistries] = useState<Group[]>([]);
  const [drivers, setDrivers] = useState<any>(null);
  const [geo, setGeo] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  // Drilldown state
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [sectorProjects, setSectorProjects] = useState<Project[]>([]);
  const [drilldownLoading, setDrilldownLoading] = useState(false);

  // Benchmark state
  const [benchmarkA, setBenchmarkA] = useState<string>("Railways");
  const [benchmarkB, setBenchmarkB] = useState<string>("Road Transport and Highways");

  useEffect(() => {
    Promise.all([
      getJson<Group[]>("/analytics/sectors"),
      getJson<Group[]>("/analytics/ministries"),
      getJson<any>("/analytics/cost-drivers").catch(() => null),
      getJson<any>("/analytics/geography").catch(() => null),
    ])
      .then(([s, m, d, g]) => {
        setSectors(s);
        setMinistries(m);
        setDrivers(d);
        setGeo(g);
        if (s.length > 0) {
          setBenchmarkA(s[0].group);
          if (s.length > 1) setBenchmarkB(s[1].group);
        }
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  // Fetch projects for drilldown whenever a sector is clicked
  useEffect(() => {
    if (!selectedSector) {
      setSectorProjects([]);
      return;
    }
    setDrilldownLoading(true);
    getJson<{ items: Project[] }>(`/projects?sector=${encodeURIComponent(selectedSector)}&limit=15`)
      .then((res) => setSectorProjects(res.items))
      .catch(() => setSectorProjects([]))
      .finally(() => setDrilldownLoading(false));
  }, [selectedSector]);

  const groupA = sectors.find((s) => s.group === benchmarkA);
  const groupB = sectors.find((s) => s.group === benchmarkB);

  return (
    <section className="section" aria-labelledby="analytics-heading">
      <div className="wrap">
        <div className="section-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
          <div>
            <p className="section-eyebrow">Portfolio Analytics & Intelligence</p>
            <h2 id="analytics-heading">Sector, Ministry & Macro Risk Analytics</h2>
            <p>
              Multidimensional analytics powered by stored model inferences, Shapley feature attributions, and cross-sector benchmarking. Click any sector to drill down.
            </p>
          </div>
          <Link to="/analytics/models" className="btn btn-secondary" style={{ fontSize: "0.85rem", padding: "8px 14px" }}>
            📊 ML Models & Calibration →
          </Link>
        </div>

        {error && <div className="alert alert-error" role="alert">{error}</div>}

        {loading ? (
          <div className="panel loading" role="status">
            <span className="spinner" /> Loading analytics data…
          </div>
        ) : (
          <>
            {/* Interactive Sector Risk Chart & Table */}
            <div className="panel" style={{ marginBottom: 20 }}>
              <div className="panel-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <p className="section-eyebrow">Sector Diagnostics</p>
                  <h3 style={{ margin: 0 }}>Average Risk Score by Sector</h3>
                </div>
                {selectedSector && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ padding: "4px 10px", fontSize: "0.8rem", minHeight: 32 }}
                    onClick={() => setSelectedSector(null)}
                  >
                    Clear Filter ({selectedSector}) ✕
                  </button>
                )}
              </div>

              <div style={{ padding: "12px 18px" }}>
                <ResponsiveContainer width="100%" height={290}>
                  <BarChart
                    data={sectors.slice(0, 10)}
                    layout="vertical"
                    margin={{ top: 4, right: 12, bottom: 4, left: 12 }}
                    onClick={(e) => {
                      if (e && e.activeLabel) {
                        setSelectedSector(String(e.activeLabel));
                      }
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    <CartesianGrid horizontal={false} stroke="#D9E1EA" />
                    <XAxis type="number" domain={[0, 100]} hide />
                    <YAxis type="category" dataKey="group" width={140} tick={{ fontSize: 12 }} />
                    <Tooltip
                      formatter={(v) => [`${formatNumber(Number(v), 1)} / 100`, "Avg Risk Score"]}
                    />
                    <Bar dataKey="average_overall_score" fill="#1F5AA6" radius={[0, 4, 4, 0]} barSize={20}>
                      {sectors.slice(0, 10).map((s) => (
                        <Cell
                          key={s.group}
                          fill={
                            selectedSector === s.group
                              ? "#F39A24"
                              : s.average_overall_score && s.average_overall_score > 60
                              ? "#C53030"
                              : "#1F5AA6"
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>

                <p style={{ fontSize: "0.8rem", color: "var(--ink-3)", marginTop: 6 }}>
                  💡 Tip: Click any bar or sector row below to filter projects by sector.
                </p>

                <div className="table-wrap" style={{ marginTop: 10 }}>
                  <table className="gov-table">
                    <thead>
                      <tr>
                        <th scope="col">Sector</th>
                        <th scope="col">Projects</th>
                        <th scope="col">Avg Risk Score</th>
                        <th scope="col">High Risk</th>
                        <th scope="col">Critical Risk</th>
                        <th scope="col" style={{ textAlign: "right" }}>Drilldown</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sectors.map((s) => (
                        <tr
                          key={s.group}
                          style={{
                            background: selectedSector === s.group ? "var(--cream)" : undefined,
                            cursor: "pointer",
                          }}
                          onClick={() => setSelectedSector(s.group === selectedSector ? null : s.group)}
                        >
                          <td>
                            <strong>{s.group}</strong>
                            {selectedSector === s.group && (
                              <span style={{ marginLeft: 8, fontSize: "0.72rem", color: "var(--saffron)", fontWeight: 700 }}>
                                ● ACTIVE SELECTION
                              </span>
                            )}
                          </td>
                          <td>{formatNumber(s.project_count)}</td>
                          <td>
                            <strong>{formatNumber(s.average_overall_score, 1)}</strong>
                          </td>
                          <td>
                            <span style={{ color: s.high_risk_projects > 0 ? "var(--warning)" : undefined, fontWeight: 600 }}>
                              {formatNumber(s.high_risk_projects)}
                            </span>
                          </td>
                          <td>
                            <span style={{ color: s.critical_projects > 0 ? "var(--error)" : undefined, fontWeight: 700 }}>
                              {formatNumber(s.critical_projects)}
                            </span>
                          </td>
                          <td style={{ textAlign: "right" }}>
                            <span className="link" style={{ fontSize: "0.82rem" }}>
                              {selectedSector === s.group ? "Close ▲" : "Inspect ▼"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Drilldown Projects View when a sector is selected */}
            {selectedSector && (
              <div className="panel" style={{ marginBottom: 20, borderLeft: "4px solid var(--saffron)" }}>
                <div className="panel-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <p className="section-eyebrow">Interactive Sector Drilldown</p>
                    <h3 style={{ margin: 0 }}>Projects in {selectedSector} ({sectorProjects.length})</h3>
                  </div>
                  <Link to={`/projects?sector=${encodeURIComponent(selectedSector)}`} className="link" style={{ fontSize: "0.85rem" }}>
                    View all in Projects Directory →
                  </Link>
                </div>

                <div style={{ padding: "4px 18px 18px" }}>
                  {drilldownLoading ? (
                    <div style={{ padding: 20, textAlign: "center" }}>
                      <span className="spinner" /> Loading {selectedSector} projects…
                    </div>
                  ) : sectorProjects.length === 0 ? (
                    <div style={{ padding: 20, textAlign: "center", color: "var(--ink-2)" }}>
                      No projects found under this sector.
                    </div>
                  ) : (
                    <div className="table-wrap">
                      <table className="gov-table">
                        <thead>
                          <tr>
                            <th scope="col">Project Code & Name</th>
                            <th scope="col">Ministry</th>
                            <th scope="col">Physical Progress</th>
                            <th scope="col">Risk Score</th>
                            <th scope="col">Risk Band</th>
                            <th scope="col" style={{ textAlign: "right" }}>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {sectorProjects.map((p) => (
                            <tr key={p.project_id}>
                              <td>
                                <strong>{p.project_name}</strong>
                                <span className="row-code">{p.project_code}</span>
                              </td>
                              <td>{p.ministry}</td>
                              <td>{formatPercent(p.physical_progress_pct)}</td>
                              <td>
                                <strong>{p.overall_score !== null ? formatNumber(p.overall_score) : "—"}</strong>
                              </td>
                              <td><Band band={p.risk_band} /></td>
                              <td style={{ textAlign: "right" }}>
                                <Link to={`/projects/${p.project_id}`} className="link" style={{ fontSize: "0.82rem" }}>
                                  View Audit →
                                </Link>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Cross-Sector Peer Benchmarking Comparator */}
            <div className="panel" style={{ marginBottom: 20 }}>
              <div className="panel-head">
                <div>
                  <p className="section-eyebrow">Peer Benchmarking</p>
                  <h3 style={{ margin: 0 }}>Comparative Sector Analysis</h3>
                </div>
              </div>

              <div style={{ padding: 18 }}>
                <div style={{ display: "flex", gap: 16, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
                  <div className="gov-form-group" style={{ minWidth: 200, flex: 1 }}>
                    <label htmlFor="bm-a">Sector A</label>
                    <select id="bm-a" value={benchmarkA} onChange={(e) => setBenchmarkA(e.target.value)}>
                      {sectors.map((s) => (
                        <option key={s.group} value={s.group}>
                          {s.group}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div style={{ alignSelf: "flex-end", paddingBottom: 10, fontWeight: 700, color: "var(--ink-3)" }}>
                    VS
                  </div>
                  <div className="gov-form-group" style={{ minWidth: 200, flex: 1 }}>
                    <label htmlFor="bm-b">Sector B</label>
                    <select id="bm-b" value={benchmarkB} onChange={(e) => setBenchmarkB(e.target.value)}>
                      {sectors.map((s) => (
                        <option key={s.group} value={s.group}>
                          {s.group}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="card-grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                  <div className="card" style={{ background: "var(--bg-alt)", border: "1px solid var(--border)" }}>
                    <h4 style={{ margin: "0 0 10px", color: "var(--navy-900)" }}>{benchmarkA}</h4>
                    <div style={{ display: "grid", gap: 8, fontSize: "0.88rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>Total Projects:</span>
                        <strong>{groupA ? formatNumber(groupA.project_count) : "—"}</strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>Average Risk Score:</span>
                        <strong>{groupA ? formatNumber(groupA.average_overall_score, 1) : "—"} / 100</strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>High Risk Projects:</span>
                        <strong style={{ color: "var(--warning)" }}>{groupA ? formatNumber(groupA.high_risk_projects) : "—"}</strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>Critical Risk Projects:</span>
                        <strong style={{ color: "var(--error)" }}>{groupA ? formatNumber(groupA.critical_projects) : "—"}</strong>
                      </div>
                    </div>
                  </div>

                  <div className="card" style={{ background: "var(--bg-alt)", border: "1px solid var(--border)" }}>
                    <h4 style={{ margin: "0 0 10px", color: "var(--navy-900)" }}>{benchmarkB}</h4>
                    <div style={{ display: "grid", gap: 8, fontSize: "0.88rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>Total Projects:</span>
                        <strong>{groupB ? formatNumber(groupB.project_count) : "—"}</strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>Average Risk Score:</span>
                        <strong>{groupB ? formatNumber(groupB.average_overall_score, 1) : "—"} / 100</strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>High Risk Projects:</span>
                        <strong style={{ color: "var(--warning)" }}>{groupB ? formatNumber(groupB.high_risk_projects) : "—"}</strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>Critical Risk Projects:</span>
                        <strong style={{ color: "var(--error)" }}>{groupB ? formatNumber(groupB.critical_projects) : "—"}</strong>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Ministry Scatter View */}
            <div className="panel" style={{ marginBottom: 20 }}>
              <div className="panel-head">
                <div>
                  <p className="section-eyebrow">Ministry Portfolio Exposure</p>
                  <h3 style={{ margin: 0 }}>Project Volume vs. Average Risk by Ministry</h3>
                </div>
              </div>
              <div style={{ padding: "12px 18px" }}>
                <ResponsiveContainer width="100%" height={260}>
                  <ScatterChart margin={{ top: 10, right: 12, bottom: 8, left: -10 }}>
                    <CartesianGrid stroke="#D9E1EA" strokeDasharray="3 3" />
                    <XAxis type="number" dataKey="x" name="Projects" tick={{ fontSize: 11 }} />
                    <YAxis type="number" dataKey="y" name="Avg score" domain={[0, 100]} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v) => formatNumber(Number(v), 1)} />
                    <Scatter
                      data={ministries.map((m) => ({ x: m.project_count, y: m.average_overall_score ?? 0, name: m.group }))}
                      fill="#174A8B"
                    >
                      {ministries.map((m) => (
                        <Cell key={m.group} fill={bandColors[m.high_risk_projects > m.critical_projects ? "high" : "low"] ?? "#174A8B"} />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
                <div className="table-wrap">
                  <table className="gov-table">
                    <thead>
                      <tr>
                        <th scope="col">Ministry</th>
                        <th scope="col">Projects Tracked</th>
                        <th scope="col">Average Score</th>
                        <th scope="col">High Risk</th>
                        <th scope="col">Critical Risk</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ministries.slice(0, 10).map((m) => (
                        <tr key={m.group}>
                          <td><strong>{m.group}</strong></td>
                          <td>{formatNumber(m.project_count)}</td>
                          <td>{formatNumber(m.average_overall_score, 1)}</td>
                          <td>{formatNumber(m.high_risk_projects)}</td>
                          <td>{formatNumber(m.critical_projects)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Cost Drivers */}
            <div className="panel" style={{ marginBottom: 20 }}>
              <div className="panel-head">
                <div>
                  <p className="section-eyebrow">Explainable AI Attributions</p>
                  <h3 style={{ margin: 0 }}>Macro Cost Risk Drivers (Mean SHAP Value)</h3>
                </div>
              </div>
              <div style={{ padding: "12px 18px" }}>
                {drivers ? (
                  <>
                    <ResponsiveContainer width="100%" height={240}>
                      <BarChart data={drivers.items.slice(0, 8)} layout="vertical" margin={{ left: 12 }}>
                        <CartesianGrid horizontal={false} stroke="#D9E1EA" />
                        <XAxis type="number" hide />
                        <YAxis type="category" dataKey="feature" width={140} tick={{ fontSize: 11 }} />
                        <Tooltip formatter={(v) => formatNumber(Number(v), 4)} />
                        <Bar dataKey="average_shap" fill="#1F5AA6" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                    <div className="table-wrap">
                      <table className="gov-table">
                        <thead>
                          <tr>
                            <th>Predictive Feature</th>
                            <th>Avg SHAP Value</th>
                            <th>Feature Coverage</th>
                          </tr>
                        </thead>
                        <tbody>
                          {drivers.items.slice(0, 8).map((d: any) => (
                            <tr key={d.feature}>
                              <td><strong>{d.feature}</strong></td>
                              <td>{formatNumber(d.average_shap, 4)}</td>
                              <td>{d.coverage}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                ) : (
                  <p>Loading feature attributions…</p>
                )}
              </div>
            </div>

            {/* Geography */}
            <div className="panel">
              <div className="panel-head">
                <div>
                  <p className="section-eyebrow">Geographic Surveillance</p>
                  <h3 style={{ margin: 0 }}>State & Regional Aggregations</h3>
                </div>
              </div>
              <div style={{ padding: "12px 18px" }}>
                {geo ? (
                  <>
                    <div className="map-panel" style={{ border: "1px solid #D9E1EA", borderRadius: 6, padding: 12, background: "#F7F9FC" }}>
                      <p style={{ fontSize: "0.8rem", color: "#52606D", margin: "0 0 10px" }}>{geo.note} · {geo.methodology}</p>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10 }}>
                        {geo.regions.slice(0, 8).map((g: any) => (
                          <div key={g.region} style={{ border: "1px solid #D9E1EA", padding: 10, borderRadius: 6, background: "#fff" }}>
                            <strong style={{ fontSize: "0.85rem", color: "var(--navy-900)" }}>{g.region}</strong>
                            <div style={{ fontSize: "0.78rem", color: "#52606D", marginTop: 2 }}>
                              {formatNumber(g.project_count)} projects · avg score {formatNumber(g.average_overall_score, 1)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="table-wrap" style={{ marginTop: 12 }}>
                      <table className="gov-table">
                        <thead>
                          <tr>
                            <th>Region</th>
                            <th>Projects</th>
                            <th>Avg Risk Score</th>
                            <th>High Risk</th>
                          </tr>
                        </thead>
                        <tbody>
                          {geo.regions.map((g: any) => (
                            <tr key={g.region}>
                              <td>{g.region}</td>
                              <td>{formatNumber(g.project_count)}</td>
                              <td>{formatNumber(g.average_overall_score, 1)}</td>
                              <td>{formatNumber(g.high_risk_projects)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                ) : (
                  <p>Loading geography…</p>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
