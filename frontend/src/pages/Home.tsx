import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import HeroArt from "../components/HeroArt";
import IndiaMap from "../components/IndiaMap";
import { Reveal, useCountUp, useReducedMotion } from "../hooks";
import { API_URL, formatNumber, getJson, type Dashboard, type Group, type Project } from "../api";

const DONUT = [
  { key: "low", color: "#16827A" },
  { key: "medium", color: "#F39A24" },
  { key: "high", color: "#C0531A" },
  { key: "critical", color: "#B42318" },
];

const SECTOR_CARDS = [
  { title: "Roads & Highways", match: ["road", "highway"], ico: "R", box: "si-blue", card: "" },
  { title: "Railways", match: ["rail"], ico: "Rl", box: "si-saffron", card: "a-saffron" },
  { title: "Urban Infrastructure", match: ["urban", "housing", "city"], ico: "U", box: "si-teal", card: "a-teal" },
  { title: "Water & Irrigation", match: ["water", "irrigation", "river"], ico: "W", box: "si-gold", card: "a-gold" },
  { title: "Energy & Power", match: ["power", "energy", "electric"], ico: "E", box: "si-navy", card: "a-navy" },
];

const JOURNEY = [
  { t: "Project Initiated", d: "Sanctioned and recorded in the snapshot.", s: "done" },
  { t: "Planning", d: "Costs, timelines and scope baselined.", s: "done" },
  { t: "Execution", d: "Expenditure and physical progress reported.", s: "done" },
  { t: "Risk Detected", d: "Stored model flags cost or time exposure.", s: "hot" },
  { t: "Review", d: "Officials examine facts and peer benchmarks.", s: "" },
  { t: "Resolution", d: "Corrective action tracked in later snapshots.", s: "" },
];

const FOCUS_IMG = [
  "https://picsum.photos/seed/nh-focus-corridor/640/420",
  "https://picsum.photos/seed/urban-metro-focus/640/420",
  "https://picsum.photos/seed/water-canal-focus/640/420",
];

const DOC_TABS = ["Methodology", "Reports", "Datasets", "Guidelines"] as const;

function bandLabel(band: string | null) {
  if (band === "low") return <span className="st st-low">Low risk</span>;
  if (band === "medium") return <span className="st st-moderate">Moderate</span>;
  if (band === "high") return <span className="st st-high">High</span>;
  if (band === "critical") return <span className="st st-critical">Critical</span>;
  return <span className="st st-na">Unavailable</span>;
}

function Kpi({ label, value, suffix, sub, accent }: { label: string; value: number | null; suffix?: string; sub: string; accent?: string }) {
  const { ref, value: v } = useCountUp(value);
  return (
    <article className={`kpi-card ${accent ?? ""}`}>
      <span className="k-label">{label}</span>
      <strong className="k-value"><span ref={ref}>{value === null ? "—" : `${formatNumber(Math.round(v))}${suffix ?? ""}`}</span></strong>
      <small>{sub}</small>
    </article>
  );
}

export default function Home() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [updates, setUpdates] = useState<{ id: number; category: string; title: string; summary: string; published_at: string }[]>([]);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [sector, setSector] = useState("");
  const [band, setBand] = useState("");
  const [tab, setTab] = useState<(typeof DOC_TABS)[number]>("Methodology");
  const reduced = useReducedMotion();
  const { ref: capRef, value: capVal } = useCountUp(dashboard ? dashboard.total_revised_cost_cr || dashboard.total_original_cost_cr : null);

  useEffect(() => {
    Promise.all([
      getJson<Dashboard>("/dashboard/summary").catch(() => null),
      getJson<{ items: Project[] }>("/projects?limit=500").catch(() => null),
      getJson<Group[]>("/analytics/sectors").catch(() => null),
      getJson<{ items: typeof updates }>("/updates?limit=3").catch(() => null),
    ]).then(([d, p, g, u]) => {
      if (!d) setError("Backend unreachable. Start it with python -m uvicorn backend.app.main:app --port 8000.");
      setDashboard(d); setProjects(p?.items ?? []); setGroups(g ?? []); setUpdates(u?.items ?? []);
    });
  }, []);

  const bandCounts = useMemo(() => {
    const c: Record<string, number> = { low: 0, medium: 0, high: 0, critical: 0 };
    projects.forEach((p) => { if (p.risk_band && c[p.risk_band] !== undefined) c[p.risk_band] += 1; });
    return DONUT.map((d) => ({ name: d.key, value: c[d.key], color: d.color }));
  }, [projects]);
  const criticalPct = useMemo(() => {
    const total = bandCounts.reduce((a, b) => a + b.value, 0);
    const crit = bandCounts.find((b) => b.name === "critical")?.value ?? 0;
    return total ? Math.round((crit / total) * 100) : 0;
  }, [bandCounts]);

  const sectorLine = useMemo(
    () => [...groups].sort((a, b) => (b.average_overall_score ?? 0) - (a.average_overall_score ?? 0)).slice(0, 8)
      .map((g) => ({ name: g.group.split(" ").slice(0, 2).join(" "), score: g.average_overall_score ?? 0, full: g.group })),
    [groups],
  );

  const sectors = useMemo(() => Array.from(new Set(projects.map((p) => p.sector))).sort(), [projects]);
  const preview = useMemo(() => projects
    .filter((p) => !q || `${p.project_name} ${p.project_code} ${p.sector}`.toLowerCase().includes(q.toLowerCase()))
    .filter((p) => !sector || p.sector === sector)
    .filter((p) => !band || p.risk_band === band)
    .slice(0, 8), [projects, q, sector, band]);

  const focus = useMemo(() => [...projects].sort((a, b) => (b.overall_score ?? -1) - (a.overall_score ?? -1)).slice(0, 3), [projects]);

  return (
    <>
      <section className="hero-v2" aria-labelledby="hero-title">
        <div className="wrap hero-grid">
          <div>
            <p className="hero-kicker">Public Infrastructure · National Monitoring</p>
            <h1 id="hero-title">Monitor infrastructure projects with transparent, accountable risk intelligence.</h1>
            <p className="lead">A national-scale monitoring interface for tracking project progress, risk indicators, implementation signals and evidence-backed insights.</p>
            <div className="hero-cta">
              <Link className="btn btn-primary" to="/dashboard">Explore Dashboard</Link>
              <Link className="btn btn-secondary" to="#how">How It Works</Link>
            </div>
            <div className="hero-meta">
              <span>Dataset: {dashboard?.dataset?.source_name ?? "awaiting backend"}</span>
              <span>Source date: {dashboard?.dataset?.source_as_of_date ?? "unavailable"}</span>
            </div>
          </div>
          <HeroArt />
        </div>
      </section>

      <div className="wrap">
        <div className="notice attention" role="note" style={{ marginTop: 20 }}>
          <div><strong>Important notice — some records may be unavailable</strong><p>Required evidence has not been provided for every project. Unavailable values are shown as unavailable, never treated as safe. <Link className="link" to="/documents">View methodology →</Link></p></div>
        </div>
        {error && <div className="alert alert-error" role="alert" style={{ marginTop: 12 }}>{error} · API: {API_URL}</div>}
      </div>

      <section className="section" aria-labelledby="snap">
        <div className="wrap">
          <Reveal><div className="section-head"><p className="section-eyebrow">National Infrastructure Snapshot</p><h2 id="snap">A consolidated view of monitored projects</h2><p>Stored risk indicators from the current snapshot. Figures update when a new completed dataset is imported.</p></div></Reveal>
          <div className="kpi-grid">
            <Kpi label="Total projects" value={dashboard?.total_projects ?? null} sub={`${formatNumber(dashboard?.available_predictions ?? null)} with stored scores`} />
            <Kpi label="High-risk projects" value={dashboard?.high_risk_projects ?? null} sub="Require closer review" accent="accent-saffron" />
            <Kpi label="Critical projects" value={dashboard?.critical_projects ?? null} sub="Highest stored exposure" accent="accent-red" />
            <article className="kpi-card accent-teal">
              <span className="k-label">Capital reported</span>
              <strong className="k-value"><span ref={capRef}>{dashboard ? `${formatNumber(capVal, 0)} cr` : "—"}</span></strong>
              <small>Reported project value, in crore</small>
            </article>
          </div>
        </div>
      </section>

      <section className="section section-ice" aria-labelledby="land">
        <div className="wrap">
          <Reveal><div className="section-head"><p className="section-eyebrow">National Infrastructure Landscape</p><h2 id="land">Infrastructure coverage across regions</h2><p>Illustrative distribution. Authoritative figures live in project records.</p></div></Reveal>
          <div className="land-grid">
            <Reveal className="photo-card">
              <img src="https://picsum.photos/seed/bharat-highway-landscape/900/700" alt="Illustrative view of a national highway corridor" loading="lazy" />
              <div className="photo-tag"><p className="kicker">Project landscape</p><h3>Roads, rail, power and public works</h3><p>Coverage across regions · April 2026 – September 2026</p></div>
            </Reveal>
            <Reveal><div className="map-panel" id="map-panel"><IndiaMap /></div></Reveal>
          </div>
        </div>
      </section>

      <section className="section" aria-labelledby="sectors">
        <div className="wrap">
          <Reveal><div className="section-head"><p className="section-eyebrow">Sectors</p><h2 id="sectors">Infrastructure across sectors</h2><p>Live project counts from <code>/analytics/sectors</code>.</p></div></Reveal>
          <div className="sector-grid">
            {SECTOR_CARDS.map((s) => {
              const count = groups.filter((g) => s.match.some((m) => g.group.toLowerCase().includes(m))).reduce((a, g) => a + g.project_count, 0);
              return (
                <Reveal key={s.title} className={`sector-card ${s.card}`}>
                  <span className={`sector-ico ${s.box}`} aria-hidden="true">{s.ico}</span>
                  <h3>{s.title}</h3>
                  <span className="count">{formatNumber(count)}</span>
                  <p>projects tracked</p>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      <section className="section section-cream" aria-labelledby="mon">
        <div className="wrap">
          <Reveal><div className="section-head"><p className="section-eyebrow">Monitoring</p><h2 id="mon">Project Monitoring Dashboard</h2><p>Review progress, implementation signals and stored risk indicators. Full records on the <Link className="link" to="/projects">Projects</Link> page.</p></div></Reveal>
          <div className="filters" role="search" aria-label="Filter preview">
            <div className="field search-field"><span><label htmlFor="hq">Search</label></span><input id="hq" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name, code or sector" /></div>
            <div className="field"><span><label htmlFor="hsector">Sector</label></span><select id="hsector" value={sector} onChange={(e) => setSector(e.target.value)}><option value="">All sectors</option>{sectors.map((s) => <option key={s} value={s}>{s}</option>)}</select></div>
            <div className="field"><span><label htmlFor="hband">Risk</label></span><select id="hband" value={band} onChange={(e) => setBand(e.target.value)}><option value="">All bands</option><option value="low">Low</option><option value="medium">Moderate</option><option value="high">High</option><option value="critical">Critical</option></select></div>
          </div>
          <div className="panel"><div className="table-wrap"><table className="gov-table">
            <thead><tr><th scope="col">Project</th><th scope="col">Sector</th><th scope="col">Progress</th><th scope="col">Risk</th><th scope="col">Updated</th><th scope="col">Action</th></tr></thead>
            <tbody>{preview.length === 0 ? <tr><td colSpan={6}>No matching projects in this snapshot.</td></tr> : preview.map((p) => (
              <tr key={p.project_id}>
                <td><strong>{p.project_name}</strong><span className="row-code">{p.project_code}</span></td>
                <td>{p.sector}</td>
                <td>{p.physical_progress_pct === null ? "—" : `${formatNumber(Number(p.physical_progress_pct), 1)}%`}</td>
                <td>{bandLabel(p.risk_band)}</td>
                <td>{p.dataset?.source_as_of_date ?? "—"}</td>
                <td><Link className="link" to={`/projects/${p.project_id}`}>View Details</Link></td>
              </tr>
            ))}</tbody>
          </table></div></div>
        </div>
      </section>

      <section className="section" aria-labelledby="risk">
        <div className="wrap">
          <Reveal><div className="section-head"><p className="section-eyebrow">Risk analytics</p><h2 id="risk">How exposure is distributed</h2><p>Live from stored predictions. Last updated with the current snapshot · Source: project records.</p></div></Reveal>
          <div className="dashboard-grid">
            <div className="panel"><div className="panel-head"><div><p className="section-eyebrow">Risk distribution</p><h3>Share by risk band</h3></div></div>
              <div style={{ padding: "6px 14px 14px" }}>
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie data={bandCounts} dataKey="value" nameKey="name" innerRadius={62} outerRadius={92} paddingAngle={2} isAnimationActive={!reduced}>
                      {bandCounts.map((b) => <Cell key={b.name} fill={b.color} />)}
                    </Pie>
                    <Tooltip formatter={(v) => formatNumber(Number(v))} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
                <p style={{ fontSize: "0.85rem", color: "#52606D" }}>Critical-risk projects represent {criticalPct}% of scored projects in this snapshot.</p>
              </div>
            </div>
            <div className="panel"><div className="panel-head"><div><p className="section-eyebrow">Risk trend</p><h3>Average score across sectors</h3></div></div>
              <div style={{ padding: "6px 14px 14px" }}>
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={sectorLine} margin={{ top: 8, right: 12, bottom: 4, left: -14 }}>
                    <CartesianGrid stroke="#D9E1EA" strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-18} dy={8} height={52} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v) => `${formatNumber(Number(v), 1)} / 100`} labelFormatter={(_, p) => p?.[0]?.payload?.full ?? ""} />
                    <Line type="monotone" dataKey="score" stroke="#164A7A" strokeWidth={2.5} dot={{ fill: "#F39A24", r: 4 }} isAnimationActive={!reduced} />
                  </LineChart>
                </ResponsiveContainer>
                <p style={{ fontSize: "0.85rem", color: "#52606D" }}>Highest average exposure sits with the leftmost sector; amber markers flag each sector value.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section section-mist" id="how" aria-labelledby="journey">
        <div className="wrap">
          <Reveal><div className="section-head"><p className="section-eyebrow">How it works</p><h2 id="journey">Project risk journey</h2><p>From initiation to resolution — where this platform adds visibility.</p></div></Reveal>
          <Reveal><div className="journey" role="list">
            {JOURNEY.map((j) => <div key={j.t} className={`j-step ${j.s}`} role="listitem"><span className="j-dot" aria-hidden="true" /><h4>{j.t}</h4><p>{j.d}</p></div>)}
          </div></Reveal>
        </div>
      </section>

      <section className="section" aria-labelledby="focus">
        <div className="wrap">
          <Reveal><div className="section-head"><p className="section-eyebrow">Projects in focus</p><h2 id="focus">Highest stored exposure right now</h2><p>Live demo records, ranked by overall score.</p></div></Reveal>
          <div className="focus-grid">
            {focus.length === 0 && <p>No scored projects in this snapshot yet.</p>}
            {focus.map((p, i) => (
              <Reveal key={p.project_id} className="focus-card">
                <img src={FOCUS_IMG[i % FOCUS_IMG.length]} alt={`Illustrative view related to ${p.project_name}`} loading="lazy" />
                <div className="focus-body">
                  <span className="focus-num">0{i + 1} · DEMO RECORD</span>
                  <h3>{p.project_name}</h3>
                  <div className="focus-meta"><span>{p.sector}</span><span>Progress {p.physical_progress_pct === null ? "—" : `${formatNumber(Number(p.physical_progress_pct), 0)}%`}</span></div>
                  <div className="focus-meta"><span>Risk</span>{bandLabel(p.risk_band)}</div>
                  <p style={{ fontSize: "0.85rem", color: "#52606D", margin: 0 }}>{p.ministry} · Score {p.overall_score === null ? "unavailable" : formatNumber(Number(p.overall_score))} / 100</p>
                  <Link className="link" to={`/projects/${p.project_id}`}>View Project →</Link>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="section section-ice" aria-labelledby="docs">
        <div className="wrap">
          <Reveal><div className="section-head"><p className="section-eyebrow">Resources</p><h2 id="docs">Official Resources &amp; Methodology</h2><p>Full documents on the <Link className="link" to="/documents">Documents</Link> page.</p></div></Reveal>
          <div className="tabs" role="tablist" aria-label="Document categories">
            {DOC_TABS.map((t) => <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}>{t}</button>)}
          </div>
          {tab === "Methodology" && <>
            <DocRow kind="md" title="Risk scoring methodology" meta="MD · Updated 12 Sep 2026 · Snapshot classification, seed 42" />
            <DocRow kind="md" title="Model limitations" meta="MD · Analytical prototype — not a forecast" />
          </>}
          {tab === "Reports" && <>
            <DocRow kind="csv" title="Projects report snapshot" meta={`CSV · ${dashboard?.dataset?.source_name ?? "awaiting backend"} · As of ${dashboard?.dataset?.source_as_of_date ?? "—"}`} />
            <DocRow kind="api" title="Dataset quality report" meta="API · GET /datasets/:id/quality · Live" to="/documents" />
          </>}
          {tab === "Datasets" && <>
            <DocRow kind="csv" title="Current snapshot dataset" meta={`ID ${dashboard?.dataset?.dataset_id ?? "—"} · Imported ${dashboard?.dataset?.imported_at ?? "—"}`} />
            <DocRow kind="api" title="Dataset quality detail" meta="Grouped counts + row-level issues" to="/documents" />
          </>}
          {tab === "Guidelines" && <>
            <DocRow kind="md" title="How to read risk scores" meta="MD · 0–100 scale · Higher means higher stored exposure" />
            <DocRow kind="md" title="Evidence requirements" meta="MD · Revised costs, dates and progress reporting" />
          </>}
        </div>
      </section>

      <section className="section" aria-labelledby="transp">
        <div className="wrap">
          <Reveal><div className="section-head"><p className="section-eyebrow">Accountability</p><h2 id="transp">Transparency &amp; Methodology</h2><p>Plain-language answers about what this platform does — and does not — claim.</p></div></Reveal>
          <div className="card-grid">
            <article className="card"><h3>How risk is computed</h3><p>Snapshot classification from reported costs, dates and progress. Logistic regression and XGBoost, calibrated per target.</p><Link className="link" to="/analytics">See analytics →</Link></article>
            <article className="card"><h3>Data quality</h3><p>Accepted rows may carry warnings. Rejected rows are excluded from scoring and listed with reasons.</p><Link className="link" to="/documents">Check quality →</Link></article>
            <article className="card"><h3>Model limitations</h3><p>Analytical prototype only. Sparse peer cohorts and missing revised figures limit comparability.</p><Link className="link" to="/help">Read FAQs →</Link></article>
          </div>
        </div>
      </section>

      <section className="section section-cream" aria-labelledby="upd">
        <div className="wrap">
          <Reveal><div className="section-head"><p className="section-eyebrow">Announcements</p><h2 id="upd">Latest updates</h2><p>Dataset, method and system notices. <Link className="link" to="/updates">View All Updates →</Link></p></div></Reveal>
          <Reveal><ul className="upd">
            {updates.length === 0 ? (
              <>
                <li><time dateTime="2026-09-13">13 SEP 2026 · Dataset update</time><h4>Snapshot classifiers retrained</h4><p>Logistic regression and XGBoost registered in SQLite; scores persisted idempotently.</p></li>
                <li className="m-saffron"><time dateTime="2026-09-12">12 SEP 2026 · Methodology</time><h4>Risk scoring methodology updated</h4><p>Missing revised figures shown as unavailable — never imputed as safe.</p></li>
                <li className="m-teal"><time dateTime="2026-09-10">10 SEP 2026 · System</time><h4>New project monitoring records added</h4><p>Snapshot import validated; quality report available under Documents.</p></li>
              </>
            ) : (
              updates.map((u) => (
                <li key={u.id}><time dateTime={u.published_at}>{new Date(u.published_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })} · {u.category}</time><h4>{u.title}</h4><p>{u.summary}</p><Link className="link" to={`/updates/${u.id}`}>View Details</Link></li>
              ))
            )}
          </ul></Reveal>
          {updates.length > 0 && <p style={{ marginTop: 12 }}><Link className="link" to="/updates">View All Updates →</Link></p>}
        </div>
      </section>

      <section className="section" aria-labelledby="ask">
        <div className="wrap">
          <Reveal><div className="ask-band">
            <p className="section-eyebrow" style={{ color: "#FBD38D" }}>Project intelligence assistant</p>
            <h3 id="ask">Ask questions about the stored portfolio</h3>
            <p>“Which projects have the highest stored risk?” · “Show projects with missing evidence.” · “Which sector has the highest average risk?”</p>
            <p style={{ fontSize: "0.8rem" }}>Responses are generated only from available project records.</p>
            <p style={{ marginTop: 12 }}><Link className="btn btn-primary" style={{ background: "#F39A24", borderColor: "#F39A24", color: "#1A1206" }} to="/dashboard">Ask the Assistant →</Link></p>
          </div></Reveal>
        </div>
      </section>

      <section className="section section-mist" aria-labelledby="hsup">
        <div className="wrap">
          <Reveal><div className="section-head"><p className="section-eyebrow">Support</p><h2 id="hsup">Help &amp; Support</h2><p>More on the <Link className="link" to="/help">Help</Link> page.</p></div></Reveal>
          <div className="faq">
            <details><summary>What does the overall score mean?</summary><p>A stored 0–100 summary of cost, time and implementation signals. Higher means higher stored exposure.</p></details>
            <details><summary>Why is a project unavailable?</summary><p>Revised costs, dates or model outputs were missing for that snapshot.</p></details>
            <details><summary>Can the assistant change a prediction?</summary><p>No. It only retrieves stored facts and model outputs, with caveats.</p></details>
          </div>
        </div>
      </section>
    </>
  );
}

function DocRow({ kind, title, meta, to }: { kind: string; title: string; meta: string; to?: string }) {
  const inner = (<><span className={`doc-ico ${kind}`} aria-hidden="true">{kind.toUpperCase()}</span><div><h4>{title}</h4><p>{meta}</p></div></>);
  return (
    <div className="doc-row">
      {inner}
      {to ? <Link className="link act" to={to}>View →</Link> : <span className="act" style={{ fontSize: "0.8rem", color: "#52606D" }}>Prototype entry</span>}
    </div>
  );
}

