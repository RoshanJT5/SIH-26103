import { useEffect, useState, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  PlusCircle,
  UploadCloud,
  Database,
  Search,
  ArrowRight,
} from "lucide-react";
import { Band, formatNumber, formatPercent, getJson, initializeDemoApi, type Project } from "../api";
import CreateProjectModal from "../components/CreateProjectModal";
import UploadDatasetModal from "../components/UploadDatasetModal";

export default function ProjectsPage() {
  const [params, setParams] = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [sectors, setSectors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const sector = params.get("sector") ?? "";
  const band = params.get("risk_band") ?? "";
  const [search, setSearch] = useState(params.get("q") ?? "");

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [initializingDemo, setInitializingDemo] = useState(false);

  const fetchProjects = useCallback(() => {
    setLoading(true);
    const qp = new URLSearchParams({ limit: "500" });
    if (sector) qp.set("sector", sector);
    if (band) qp.set("risk_band", band);
    getJson<{ items: Project[] }>(`/projects?${qp.toString()}`)
      .then((r) => {
        setProjects(r.items);
        setSectors(Array.from(new Set(r.items.map((p) => p.sector))).sort());
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sector, band]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleInitDemo = async () => {
    setInitializingDemo(true);
    setError("");
    try {
      await initializeDemoApi();
      fetchProjects();
    } catch (err: any) {
      setError(err?.message || "Failed to initialize demo MoSPI portfolio.");
    } finally {
      setInitializingDemo(false);
    }
  };

  const visible = projects.filter((p) => !search || `${p.project_name} ${p.project_code} ${p.sector}`.toLowerCase().includes(search.toLowerCase()));

  return (
    <section className="section" aria-labelledby="t">
      <div className="wrap">
        <div className="section-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
          <div>
            <p className="section-eyebrow">Projects</p>
            <h2 id="t">Infrastructure Project Records</h2>
            <p>Real-time MoSPI monitoring repository with ML risk categorization. Select a project to inspect details.</p>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setIsUploadOpen(true)}
              style={{ fontSize: "0.85rem", padding: "8px 14px", display: "inline-flex", alignItems: "center", gap: 6 }}
            >
              <UploadCloud size={16} /> Ingest Dataset
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setIsCreateOpen(true)}
              style={{ fontSize: "0.85rem", padding: "8px 14px", display: "inline-flex", alignItems: "center", gap: 6 }}
            >
              <PlusCircle size={16} /> Register New Project
            </button>
          </div>
        </div>

        {!loading && projects.length === 0 && (
          <div className="zero-banner">
            <div className="zero-banner-content">
              <h4>No Infrastructure Projects Loaded</h4>
              <p>Initialize the official MoSPI repository containing 1,775 baseline central projects or register a new project.</p>
            </div>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleInitDemo}
              disabled={initializingDemo}
              style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
            >
              <Database size={16} /> {initializingDemo ? "Initializing MoSPI Baseline…" : "Load Baseline MoSPI Dataset"}
            </button>
          </div>
        )}

        <div className="filters" role="search" aria-label="Filter projects">
          <div className="field search-field">
            <span>
              <label htmlFor="q" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <Search size={14} /> Search
              </label>
            </span>
            <input id="q" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name, code or sector" />
          </div>
          <div className="field"><span><label htmlFor="sector">Sector</label></span>
            <select id="sector" value={sector} onChange={(e) => { const next = new URLSearchParams(params); if (e.target.value) next.set("sector", e.target.value); else next.delete("sector"); setParams(next); }}>
              <option value="">All sectors</option>{sectors.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="field"><span><label htmlFor="band">Risk band</label></span>
            <select id="band" value={band} onChange={(e) => { const next = new URLSearchParams(params); if (e.target.value) next.set("risk_band", e.target.value); else next.delete("risk_band"); setParams(next); }}>
              <option value="">All bands</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
            </select>
          </div>
          <span style={{ fontSize: "0.85rem", color: "#4B5563" }}>{visible.length} records</span>
        </div>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        {loading ? <div className="panel loading" role="status"><span className="spinner" />Loading projects…</div> : (
          <div className="panel"><div className="table-wrap"><table className="gov-table">
            <thead><tr><th scope="col">Project</th><th scope="col">Sector</th><th scope="col">Progress</th><th scope="col">Score</th><th scope="col">Status</th><th scope="col">Action</th></tr></thead>
            <tbody>{visible.map((p) => (
              <tr key={p.project_id}>
                <td><strong>{p.project_name}</strong><span className="row-code">{p.project_code} · {p.ministry}</span></td>
                <td>{p.sector}</td>
                <td>{formatPercent(p.physical_progress_pct)}</td>
                <td><strong>{p.overall_score === null ? "—" : formatNumber(p.overall_score)}</strong></td>
                <td><Band band={p.risk_band} /></td>
                <td>
                  <Link className="link" to={`/projects/${p.project_id}`} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                    View <ArrowRight size={14} />
                  </Link>
                </td>
              </tr>
            ))}</tbody>
          </table></div></div>
        )}

        <CreateProjectModal
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          onCreated={() => {
            fetchProjects();
          }}
        />

        <UploadDatasetModal
          isOpen={isUploadOpen}
          onClose={() => setIsUploadOpen(false)}
          onUploaded={() => {
            fetchProjects();
          }}
        />
      </div>
    </section>
  );
}
