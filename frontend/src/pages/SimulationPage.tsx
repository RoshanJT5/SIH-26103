import { useEffect, useState, useMemo } from "react";
import { useSearchParams, Link } from "react-router-dom";
import {
  Sliders,
  Play,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  RotateCcw,
  Sparkles,
  Zap,
  Building2,
  Calendar,
  IndianRupee,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Info,
} from "lucide-react";
import {
  getJson,
  formatNumber,
  simulateProjectApi,
  type Project,
  type SimulationResponse,
} from "../api";

export default function SimulationPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialProjectId = searchParams.get("project_id") || "1";

  const [projectIdInput, setProjectIdInput] = useState(initialProjectId);
  const [projectsList, setProjectsList] = useState<Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(false);

  // Form simulation values
  const [progress, setProgress] = useState<number | "">("");
  const [revisedCost, setRevisedCost] = useState<number | "">("");
  const [expenditure, setExpenditure] = useState<number | "">("");
  const [scheduleDays, setScheduleDays] = useState<number | "">("");

  // Result and baseline state
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetchingBaseline, setFetchingBaseline] = useState(false);
  const [error, setError] = useState("");

  // 1. Fetch recent project list for quick selection dropdown
  useEffect(() => {
    setProjectsLoading(true);
    getJson<{ items: Project[] }>("/projects?limit=50")
      .then((res) => {
        if (res?.items) {
          setProjectsList(res.items);
        }
      })
      .catch(() => {
        // Fallback silently if projects list cannot be loaded
      })
      .finally(() => setProjectsLoading(false));
  }, []);

  // 2. Load baseline project data whenever project ID changes
  const loadProjectBaseline = async (id: string | number) => {
    if (!id) return;
    setFetchingBaseline(true);
    setError("");
    try {
      // Call simulation with just project_id to extract baseline respective values
      const baseResult = await simulateProjectApi({ project_id: id });
      setResult(baseResult);
      setProjectIdInput(String(baseResult.project_id));
      setSearchParams({ project_id: String(baseResult.project_id) });

      // Populate input states with project's actual respective values
      setProgress(
        baseResult.baseline_physical_progress_pct !== null && baseResult.baseline_physical_progress_pct !== undefined
          ? Number(baseResult.baseline_physical_progress_pct)
          : ""
      );
      setRevisedCost(
        baseResult.baseline_revised_cost_cr !== null && baseResult.baseline_revised_cost_cr !== undefined
          ? Number(baseResult.baseline_revised_cost_cr)
          : baseResult.original_cost_cr !== null && baseResult.original_cost_cr !== undefined
          ? Number(baseResult.original_cost_cr)
          : ""
      );
      setExpenditure(
        baseResult.baseline_expenditure_cr !== null && baseResult.baseline_expenditure_cr !== undefined
          ? Number(baseResult.baseline_expenditure_cr)
          : ""
      );
      setScheduleDays(
        baseResult.baseline_schedule_revision_days !== null && baseResult.baseline_schedule_revision_days !== undefined
          ? Number(baseResult.baseline_schedule_revision_days)
          : 0
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Failed to load project baseline: ${msg}`);
    } finally {
      setFetchingBaseline(false);
    }
  };

  useEffect(() => {
    if (initialProjectId) {
      loadProjectBaseline(initialProjectId);
    }
  }, [initialProjectId]);

  // 3. Run simulation with specified or tweaked values
  const runSimulation = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!projectIdInput) {
      setError("Please specify a Project ID or Project Code.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const payload: any = {
        project_id: projectIdInput.trim(),
      };
      if (progress !== "") payload.physical_progress_pct = Number(progress);
      if (revisedCost !== "") payload.revised_cost_cr = Number(revisedCost);
      if (expenditure !== "") payload.expenditure_cr = Number(expenditure);
      if (scheduleDays !== "") payload.schedule_revision_days = Number(scheduleDays);

      const simRes = await simulateProjectApi(payload);
      setResult(simRes);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Simulation failed: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  // Helper scenario presets
  const handleResetToBaseline = () => {
    if (!result) return;
    setProgress(
      result.baseline_physical_progress_pct !== null && result.baseline_physical_progress_pct !== undefined
        ? Number(result.baseline_physical_progress_pct)
        : ""
    );
    setRevisedCost(
      result.baseline_revised_cost_cr !== null && result.baseline_revised_cost_cr !== undefined
        ? Number(result.baseline_revised_cost_cr)
        : result.original_cost_cr !== null && result.original_cost_cr !== undefined
        ? Number(result.original_cost_cr)
        : ""
    );
    setExpenditure(
      result.baseline_expenditure_cr !== null && result.baseline_expenditure_cr !== undefined
        ? Number(result.baseline_expenditure_cr)
        : ""
    );
    setScheduleDays(
      result.baseline_schedule_revision_days !== null && result.baseline_schedule_revision_days !== undefined
        ? Number(result.baseline_schedule_revision_days)
        : 0
    );
    // Immediately execute simulation for baseline
    simulateProjectApi({ project_id: result.project_id }).then(setResult).catch(() => null);
  };

  const handlePresetAccelerate = () => {
    if (!result) return;
    const baseProg = Number(result.baseline_physical_progress_pct ?? 0);
    const newProg = Math.min(100, Number((baseProg + 15).toFixed(1)));
    setProgress(newProg);
    const baseDays = Number(result.baseline_schedule_revision_days ?? 0);
    const newDays = Math.max(0, baseDays - 45);
    setScheduleDays(newDays);
  };

  const handlePresetCostEscalation = () => {
    if (!result) return;
    const baseCost = Number(result.baseline_revised_cost_cr ?? result.original_cost_cr ?? 100);
    const newCost = Number((baseCost * 1.2).toFixed(2));
    setRevisedCost(newCost);
  };

  // Derived deltas
  const progressDelta = useMemo(() => {
    if (!result || progress === "" || result.baseline_physical_progress_pct === null) return null;
    return Number(progress) - Number(result.baseline_physical_progress_pct);
  }, [result, progress]);

  const costDelta = useMemo(() => {
    if (!result || revisedCost === "") return null;
    const base = Number(result.baseline_revised_cost_cr ?? result.original_cost_cr ?? 0);
    return Number(revisedCost) - base;
  }, [result, revisedCost]);

  const expenditureDelta = useMemo(() => {
    if (!result || expenditure === "" || result.baseline_expenditure_cr === null) return null;
    return Number(expenditure) - Number(result.baseline_expenditure_cr);
  }, [result, expenditure]);

  const scheduleDelta = useMemo(() => {
    if (!result || scheduleDays === "") return null;
    const base = Number(result.baseline_schedule_revision_days ?? 0);
    return Number(scheduleDays) - base;
  }, [result, scheduleDays]);

  const getBandBadgeClass = (band?: string | null) => {
    const b = (band || "").toLowerCase();
    if (b === "low") return "badge-low";
    if (b === "medium") return "badge-medium";
    if (b === "high") return "badge-high";
    if (b === "critical") return "badge-critical";
    return "";
  };

  return (
    <section className="section" aria-labelledby="sim-title">
      <div className="wrap">
        {/* Header */}
        <div className="section-head" style={{ marginBottom: 20 }}>
          <p className="section-eyebrow">Predictions · What-If Policy Engine</p>
          <h1 id="sim-title" style={{ display: "flex", alignItems: "center", gap: 10, margin: "4px 0 8px", fontSize: "1.8rem", color: "var(--navy-900)" }}>
            <Sliders size={26} color="var(--navy-700)" /> Counterfactual Project Simulation
          </h1>
          <p style={{ color: "var(--ink-2)", maxWidth: 840, margin: 0 }}>
            Simulate the multi-factor risk impact of policy decisions, progress catch-up acceleration, budget revisions, or commissioning timeline compressions in an isolated, read-only sandbox.
          </p>
        </div>

        {/* Project Selector Bar */}
        <div className="panel" style={{ padding: "16px 20px", marginBottom: 20, background: "var(--ice)", border: "1px solid #DCE6F2" }}>
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-end", gap: 16 }}>
            <div style={{ flex: "1 1 240px" }}>
              <label htmlFor="project-picker" style={{ display: "block", fontSize: "0.82rem", fontWeight: 700, color: "var(--navy-900)", marginBottom: 6 }}>
                Choose Monitored Project from Dataset:
              </label>
              <select
                id="project-picker"
                value={projectIdInput}
                onChange={(e) => {
                  setProjectIdInput(e.target.value);
                  loadProjectBaseline(e.target.value);
                }}
                disabled={projectsLoading || fetchingBaseline}
                style={{
                  width: "100%",
                  height: 40,
                  borderRadius: 6,
                  border: "1px solid var(--border)",
                  padding: "0 10px",
                  fontSize: "0.9rem",
                  background: "#fff",
                }}
              >
                {projectsLoading && <option value="">Loading monitored projects…</option>}
                {!projectsLoading && projectsList.map((p) => (
                  <option key={p.project_id} value={p.project_id}>
                    {p.project_code} — {p.project_name} ({p.sector})
                  </option>
                ))}
              </select>
            </div>

            <div style={{ flex: "0 1 200px" }}>
              <label htmlFor="manual-pid" style={{ display: "block", fontSize: "0.82rem", fontWeight: 700, color: "var(--navy-900)", marginBottom: 6 }}>
                Or Enter Project ID / Code:
              </label>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  id="manual-pid"
                  value={projectIdInput}
                  onChange={(e) => setProjectIdInput(e.target.value)}
                  placeholder="e.g. 1 or P-001"
                  style={{ height: 40, borderRadius: 6, padding: "0 10px", fontSize: "0.9rem" }}
                />
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => loadProjectBaseline(projectIdInput)}
                  disabled={fetchingBaseline || !projectIdInput}
                  style={{ minHeight: 40, padding: "0 14px", fontSize: "0.85rem", whiteSpace: "nowrap" }}
                >
                  {fetchingBaseline ? "Loading…" : "Load"}
                </button>
              </div>
            </div>

            {result && (
              <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
                <Link
                  to={`/projects/${result.project_id}`}
                  className="btn btn-secondary"
                  style={{ minHeight: 40, padding: "0 14px", fontSize: "0.85rem", display: "inline-flex", alignItems: "center", gap: 6 }}
                >
                  View Live Dossier <ArrowRight size={14} />
                </Link>
              </div>
            )}
          </div>
        </div>

        {error && <div className="alert alert-error" role="alert" style={{ marginBottom: 20 }}>{error}</div>}

        {/* Project Baseline Details Card */}
        {result && (
          <div className="card" style={{ marginBottom: 20, borderLeft: "4px solid var(--navy-700)", background: "#fff" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <span style={{ fontWeight: 700, color: "var(--navy-900)", fontSize: "1.1rem" }}>
                    {result.project_code}
                  </span>
                  <span className={`badge ${getBandBadgeClass(result.original_band)}`}>
                    Baseline: {result.original_band?.toUpperCase()} RISK ({formatNumber(result.original_overall_score, 1)})
                  </span>
                </div>
                <h3 style={{ margin: "4px 0", fontSize: "1.1rem", color: "var(--navy-900)" }}>
                  {result.project_name || "Baseline Project Snapshot"}
                </h3>
                <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--ink-2)" }}>
                  {result.ministry} · {result.sector}
                </p>
              </div>

              {/* Baseline Summary Metrics */}
              <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
                <div style={{ textAlign: "right" }}>
                  <span style={{ fontSize: "0.74rem", textTransform: "uppercase", color: "var(--ink-3)", fontWeight: 700 }}>
                    Original Cost
                  </span>
                  <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--navy-900)" }}>
                    ₹{formatNumber(result.original_cost_cr, 2)} Cr
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <span style={{ fontSize: "0.74rem", textTransform: "uppercase", color: "var(--ink-3)", fontWeight: 700 }}>
                    Current Revised
                  </span>
                  <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--navy-900)" }}>
                    ₹{formatNumber(result.baseline_revised_cost_cr, 2)} Cr
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <span style={{ fontSize: "0.74rem", textTransform: "uppercase", color: "var(--ink-3)", fontWeight: 700 }}>
                    Current Progress
                  </span>
                  <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--navy-900)" }}>
                    {formatNumber(result.baseline_physical_progress_pct, 1)}%
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Main Grid: Form Controls & Live Output */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: 24, alignItems: "start" }}>
          {/* Left Column: Interactive Scenario Controls */}
          <div className="panel" style={{ padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ margin: 0, fontSize: "1.1rem", display: "flex", alignItems: "center", gap: 8, color: "var(--navy-900)" }}>
                <Sliders size={18} color="var(--navy-700)" /> Respective Parameters
              </h3>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleResetToBaseline}
                disabled={!result || loading}
                style={{ fontSize: "0.8rem", padding: "6px 10px", display: "inline-flex", alignItems: "center", gap: 4 }}
                title="Reset all inputs back to project's baseline values"
              >
                <RotateCcw size={13} /> Reset Baseline
              </button>
            </div>

            {/* Quick Scenario Buttons */}
            <div style={{ marginBottom: 18, display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={handlePresetAccelerate}
                className="btn btn-secondary"
                style={{ fontSize: "0.78rem", padding: "6px 10px", display: "inline-flex", alignItems: "center", gap: 4 }}
              >
                <Zap size={13} color="var(--teal)" /> Accelerate Progress (+15%)
              </button>
              <button
                type="button"
                onClick={handlePresetCostEscalation}
                className="btn btn-secondary"
                style={{ fontSize: "0.78rem", padding: "6px 10px", display: "inline-flex", alignItems: "center", gap: 4 }}
              >
                <AlertTriangle size={13} color="var(--error)" /> Cost Overrun (+20%)
              </button>
            </div>

            <form onSubmit={runSimulation} style={{ display: "grid", gap: 18 }}>
              {/* Parameter 1: Physical Progress */}
              <div className="field">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <label htmlFor="sim-prog" style={{ fontWeight: 600, fontSize: "0.88rem" }}>
                    Simulated Physical Progress (%)
                  </label>
                  {progressDelta !== null && progressDelta !== 0 && (
                    <span style={{ fontSize: "0.78rem", fontWeight: 700, color: progressDelta > 0 ? "var(--teal)" : "var(--error)" }}>
                      {progressDelta > 0 ? `+${progressDelta.toFixed(1)}%` : `${progressDelta.toFixed(1)}%`} vs Baseline
                    </span>
                  )}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <input
                    id="sim-prog"
                    type="number"
                    min={0}
                    max={100}
                    step={0.5}
                    value={progress}
                    onChange={(e) => setProgress(e.target.value === "" ? "" : Number(e.target.value))}
                    placeholder="e.g. 65"
                    style={{ width: 100, height: 38 }}
                  />
                  <input
                    type="range"
                    min={0}
                    max={100}
                    step={1}
                    value={progress === "" ? 0 : Number(progress)}
                    onChange={(e) => setProgress(Number(e.target.value))}
                    style={{ flex: 1 }}
                  />
                  <span style={{ minWidth: 45, textAlign: "right", fontSize: "0.85rem", fontWeight: 600 }}>
                    {progress === "" ? "—" : `${progress}%`}
                  </span>
                </div>
              </div>

              {/* Parameter 2: Revised Cost */}
              <div className="field">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <label htmlFor="sim-rev" style={{ fontWeight: 600, fontSize: "0.88rem" }}>
                    Simulated Revised Cost (₹ Crores)
                  </label>
                  {costDelta !== null && costDelta !== 0 && (
                    <span style={{ fontSize: "0.78rem", fontWeight: 700, color: costDelta > 0 ? "var(--error)" : "var(--teal)" }}>
                      {costDelta > 0 ? `+₹${costDelta.toFixed(2)} Cr` : `-₹${Math.abs(costDelta).toFixed(2)} Cr`} vs Baseline
                    </span>
                  )}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <input
                    id="sim-rev"
                    type="number"
                    min={0}
                    step={1}
                    value={revisedCost}
                    onChange={(e) => setRevisedCost(e.target.value === "" ? "" : Number(e.target.value))}
                    placeholder="e.g. 2400"
                    style={{ width: 140, height: 38 }}
                  />
                  <span style={{ fontSize: "0.85rem", color: "var(--ink-2)" }}>
                    Original: ₹{result ? formatNumber(result.original_cost_cr, 2) : "—"} Cr
                  </span>
                </div>
              </div>

              {/* Parameter 3: Cumulative Expenditure */}
              <div className="field">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <label htmlFor="sim-exp" style={{ fontWeight: 600, fontSize: "0.88rem" }}>
                    Simulated Cumulative Expenditure (₹ Crores)
                  </label>
                  {expenditureDelta !== null && expenditureDelta !== 0 && (
                    <span style={{ fontSize: "0.78rem", fontWeight: 700, color: expenditureDelta > 0 ? "var(--error)" : "var(--teal)" }}>
                      {expenditureDelta > 0 ? `+₹${expenditureDelta.toFixed(2)} Cr` : `-₹${Math.abs(expenditureDelta).toFixed(2)} Cr`}
                    </span>
                  )}
                </div>
                <input
                  id="sim-exp"
                  type="number"
                  min={0}
                  step={1}
                  value={expenditure}
                  onChange={(e) => setExpenditure(e.target.value === "" ? "" : Number(e.target.value))}
                  placeholder="e.g. 800"
                  style={{ height: 38 }}
                />
              </div>

              {/* Parameter 4: Schedule Revision Delay Days */}
              <div className="field">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <label htmlFor="sim-delay" style={{ fontWeight: 600, fontSize: "0.88rem" }}>
                    Schedule Revision (Days from Sanction/Original)
                  </label>
                  {scheduleDelta !== null && scheduleDelta !== 0 && (
                    <span style={{ fontSize: "0.78rem", fontWeight: 700, color: scheduleDelta > 0 ? "var(--error)" : "var(--teal)" }}>
                      {scheduleDelta > 0 ? `+${scheduleDelta} days delay` : `${scheduleDelta} days accelerated`}
                    </span>
                  )}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <input
                    id="sim-delay"
                    type="number"
                    min={0}
                    step={15}
                    value={scheduleDays}
                    onChange={(e) => setScheduleDays(e.target.value === "" ? "" : Number(e.target.value))}
                    placeholder="e.g. 180"
                    style={{ width: 120, height: 38 }}
                  />
                  <span style={{ fontSize: "0.85rem", color: "var(--ink-2)" }}>
                    Baseline delay: {result ? `${result.baseline_schedule_revision_days ?? 0} days` : "—"}
                  </span>
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading || fetchingBaseline}
                style={{
                  minHeight: 44,
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  fontSize: "0.95rem",
                  fontWeight: 600,
                  marginTop: 6,
                }}
              >
                <Play size={16} /> {loading ? "Evaluating What-If Model…" : "Recalculate Simulated Risk"}
              </button>
            </form>
          </div>

          {/* Right Column: Simulation Results & Delta Card */}
          <div>
            {result ? (
              <div className="panel" style={{ padding: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                  <h3 style={{ margin: 0, fontSize: "1.1rem", display: "flex", alignItems: "center", gap: 8, color: "var(--navy-900)" }}>
                    <Activity size={18} color="var(--navy-700)" /> Simulated Risk Outcome
                  </h3>
                  <span style={{ fontSize: "0.78rem", color: "var(--ink-3)", textTransform: "uppercase", fontWeight: 700 }}>
                    Sandbox Inference
                  </span>
                </div>

                {/* Score Comparison Display */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr auto 1fr",
                    gap: 16,
                    alignItems: "center",
                    padding: "16px",
                    borderRadius: 8,
                    background: "var(--bg-alt)",
                    marginBottom: 18,
                    textAlign: "center",
                  }}
                >
                  {/* Baseline Column */}
                  <div>
                    <span style={{ fontSize: "0.75rem", textTransform: "uppercase", color: "var(--ink-3)", fontWeight: 700 }}>
                      Baseline Score
                    </span>
                    <div style={{ fontSize: "2rem", fontWeight: 800, color: "var(--navy-900)", lineHeight: 1.1, margin: "4px 0" }}>
                      {formatNumber(result.original_overall_score, 1)}
                    </div>
                    <span className={`badge ${getBandBadgeClass(result.original_band)}`}>
                      {result.original_band?.toUpperCase()}
                    </span>
                  </div>

                  {/* Transition Arrow */}
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                    <ArrowRight size={22} color="var(--navy-700)" />
                    {result.delta !== null && (
                      <span
                        style={{
                          fontSize: "0.82rem",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: 12,
                          background:
                            Number(result.delta) > 0.05
                              ? "#FEE4E2"
                              : Number(result.delta) < -0.05
                              ? "#D1FADF"
                              : "#EAECF0",
                          color:
                            Number(result.delta) > 0.05
                              ? "#B42318"
                              : Number(result.delta) < -0.05
                              ? "#027A48"
                              : "#344054",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 3,
                        }}
                      >
                        {Number(result.delta) > 0.05 ? (
                          <>
                            <TrendingUp size={13} /> +{formatNumber(result.delta, 1)}
                          </>
                        ) : Number(result.delta) < -0.05 ? (
                          <>
                            <TrendingDown size={13} /> {formatNumber(result.delta, 1)}
                          </>
                        ) : (
                          <>Matches Baseline</>
                        )}
                      </span>
                    )}
                  </div>

                  {/* Simulated Column */}
                  <div>
                    <span style={{ fontSize: "0.75rem", textTransform: "uppercase", color: "var(--ink-3)", fontWeight: 700 }}>
                      Simulated Score
                    </span>
                    <div
                      style={{
                        fontSize: "2rem",
                        fontWeight: 800,
                        color:
                          result.simulated_band === "critical"
                            ? "var(--error)"
                            : result.simulated_band === "high"
                            ? "var(--saffron)"
                            : "var(--navy-900)",
                        lineHeight: 1.1,
                        margin: "4px 0",
                      }}
                    >
                      {formatNumber(result.simulated_overall_score, 1)}
                    </div>
                    <span className={`badge ${getBandBadgeClass(result.simulated_band)}`}>
                      {result.simulated_band?.toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Component Breakdown Table */}
                <h4 style={{ margin: "0 0 8px", fontSize: "0.92rem", color: "var(--navy-900)" }}>
                  Factor Breakdown Comparison
                </h4>
                <div className="table-wrap" style={{ marginBottom: 18 }}>
                  <table style={{ fontSize: "0.85rem", width: "100%" }}>
                    <thead>
                      <tr>
                        <th>Risk Dimension</th>
                        <th style={{ textAlign: "right" }}>Baseline</th>
                        <th style={{ textAlign: "right" }}>Simulated</th>
                        <th style={{ textAlign: "right" }}>Shift</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td><strong>Cost Risk (40%)</strong></td>
                        <td style={{ textAlign: "right" }}>{formatNumber(result.original_cost_score, 1)}</td>
                        <td style={{ textAlign: "right" }}>{formatNumber(result.simulated_cost_score, 1)}</td>
                        <td style={{ textAlign: "right", fontWeight: 700, color: (result.simulated_cost_score ?? 0) > (result.original_cost_score ?? 0) ? "var(--error)" : "var(--teal)" }}>
                          {formatNumber((result.simulated_cost_score ?? 0) - (result.original_cost_score ?? 0), 1)}
                        </td>
                      </tr>
                      <tr>
                        <td><strong>Schedule Risk (40%)</strong></td>
                        <td style={{ textAlign: "right" }}>{formatNumber(result.original_time_score, 1)}</td>
                        <td style={{ textAlign: "right" }}>{formatNumber(result.simulated_time_score, 1)}</td>
                        <td style={{ textAlign: "right", fontWeight: 700, color: (result.simulated_time_score ?? 0) > (result.original_time_score ?? 0) ? "var(--error)" : "var(--teal)" }}>
                          {formatNumber((result.simulated_time_score ?? 0) - (result.original_time_score ?? 0), 1)}
                        </td>
                      </tr>
                      <tr>
                        <td><strong>Implementation Risk (20%)</strong></td>
                        <td style={{ textAlign: "right" }}>{formatNumber(result.original_implementation_score, 1)}</td>
                        <td style={{ textAlign: "right" }}>{formatNumber(result.simulated_implementation_score, 1)}</td>
                        <td style={{ textAlign: "right", fontWeight: 700, color: (result.simulated_implementation_score ?? 0) > (result.original_implementation_score ?? 0) ? "var(--error)" : "var(--teal)" }}>
                          {formatNumber((result.simulated_implementation_score ?? 0) - (result.original_implementation_score ?? 0), 1)}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                {/* Assumptions and Model Attributions */}
                <h4 style={{ margin: "0 0 6px", fontSize: "0.92rem", color: "var(--navy-900)" }}>
                  Model Assumptions &amp; Inferences
                </h4>
                <ul style={{ paddingLeft: 18, margin: "0 0 14px" }}>
                  {result.assumptions.map((a: string, idx: number) => (
                    <li key={idx} style={{ fontSize: "0.84rem", color: "var(--ink-2)", marginBottom: 4 }}>
                      {a}
                    </li>
                  ))}
                </ul>

                <p style={{ fontSize: "0.78rem", color: "var(--ink-3)", margin: 0, fontStyle: "italic", borderTop: "1px solid var(--border)", paddingTop: 8 }}>
                  {result.note}
                </p>
              </div>
            ) : (
              <div className="panel" style={{ padding: 32, textAlign: "center", color: "var(--ink-2)" }}>
                <span className="spinner" /> Loading project baseline data…
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
