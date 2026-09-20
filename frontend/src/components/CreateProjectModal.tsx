import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  X,
  CheckCircle2,
  FolderPlus,
  ArrowRight,
  ArrowLeft,
  PlusCircle,
  Clock,
} from "lucide-react";
import { createProjectApi, type CreateProjectPayload, type CreateProjectResult } from "../api";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onCreated?: (result: CreateProjectResult) => void;
}

const COMMON_SECTORS = [
  "Railways",
  "Road Transport and Highways",
  "Power",
  "Petroleum",
  "Urban Development",
  "Coal",
  "Civil Aviation",
  "Shipping and Ports",
  "Telecommunications",
  "Atomic Energy",
  "Steel",
  "Mines",
];

export default function CreateProjectModal({ isOpen, onClose, onCreated }: Props) {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<CreateProjectPayload>({
    project_code: `PRJ-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`,
    project_name: "",
    sector: "Railways",
    ministry: "Ministry of Railways",
    implementing_agency: "Rail Vikas Nigam Limited",
    original_cost_cr: 1000,
    revised_cost_cr: null,
    expenditure_cr: 250,
    physical_progress_pct: 25,
    original_commissioning_date: "2027-12-31",
    revised_commissioning_date: null,
    sanction_date: "2022-04-01",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CreateProjectResult | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const payload: CreateProjectPayload = {
        ...formData,
        original_cost_cr: Number(formData.original_cost_cr),
        revised_cost_cr: formData.revised_cost_cr ? Number(formData.revised_cost_cr) : null,
        expenditure_cr: Number(formData.expenditure_cr || 0),
        physical_progress_pct: Number(formData.physical_progress_pct || 0),
      };

      const res = await createProjectApi(payload);
      setResult(res);
      if (onCreated) onCreated(res);
    } catch (err: any) {
      setError(err?.message || "Failed to create project. Please verify inputs.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoToProject = () => {
    if (result) {
      onClose();
      navigate(result.redirect_url);
    }
  };

  return (
    <div className="gov-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="create-proj-title">
      <div className="gov-modal modal-wide">
        <div className="gov-modal-header">
          <div>
            <h3 id="create-proj-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <FolderPlus size={22} color="var(--navy-700)" />
              Register New Infrastructure Project
            </h3>
            <p>Add single project to live MoSPI monitoring portfolio with automatic ML risk scoring</p>
          </div>
          <button type="button" className="gov-modal-close" onClick={onClose} aria-label="Close dialog">
            <X size={20} />
          </button>
        </div>

        {result ? (
          <div className="gov-modal-body">
            <div style={{ textAlign: "center", padding: "16px 8px" }}>
              <div
                style={{
                  width: 60,
                  height: 60,
                  borderRadius: "50%",
                  background: "#E6F4EA",
                  color: "#137333",
                  display: "grid",
                  placeItems: "center",
                  margin: "0 auto 12px",
                }}
              >
                <CheckCircle2 size={36} />
              </div>
              <h4 style={{ margin: "0 0 6px", color: "var(--navy-900)", fontSize: "1.2rem" }}>
                Project Registered & Scored Successfully!
              </h4>
              <p style={{ margin: "0 0 16px", color: "var(--ink-2)", fontSize: "0.9rem" }}>
                <strong>{result.project_code}</strong>: {result.project_name}
              </p>

              <div
                style={{
                  display: "flex",
                  justifyContent: "center",
                  gap: 20,
                  margin: "20px 0",
                  flexWrap: "wrap",
                }}
              >
                <div style={{ background: "var(--bg-alt)", padding: "12px 20px", borderRadius: 8, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--ink-3)", textTransform: "uppercase" }}>Overall Risk Score</div>
                  <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--navy-900)" }}>
                    {result.overall_score !== null ? result.overall_score : "Pending"}
                  </div>
                </div>
                <div style={{ background: "var(--bg-alt)", padding: "12px 20px", borderRadius: 8, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--ink-3)", textTransform: "uppercase" }}>Assigned Risk Band</div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 700, textTransform: "capitalize", color: result.risk_band === "critical" ? "#B42318" : result.risk_band === "high" ? "#C0531A" : "#16803C" }}>
                    {result.risk_band || "Evaluated"}
                  </div>
                </div>
              </div>
            </div>

            <div className="gov-modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <ArrowLeft size={16} /> Back to Projects
              </button>
              <button type="button" className="btn btn-primary" onClick={handleGoToProject} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                Open Project Overview & Risk Profile <ArrowRight size={16} />
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="gov-modal-body">
              {error && (
                <div className="alert alert-error" role="alert" style={{ marginBottom: 12 }}>
                  {error}
                </div>
              )}

              <div className="form-grid-2">
                <div className="gov-form-group">
                  <label htmlFor="pcode">Project Code *</label>
                  <input
                    id="pcode"
                    required
                    value={formData.project_code}
                    onChange={(e) => setFormData({ ...formData, project_code: e.target.value })}
                    placeholder="e.g. MOR-2026-001"
                  />
                  <span className="form-hint">Official MoSPI or Ministry unique identifier</span>
                </div>

                <div className="gov-form-group">
                  <label htmlFor="pname">Project Title *</label>
                  <input
                    id="pname"
                    required
                    value={formData.project_name}
                    onChange={(e) => setFormData({ ...formData, project_name: e.target.value })}
                    placeholder="e.g. Eastern Dedicated Freight Corridor Package 3"
                  />
                </div>
              </div>

              <div className="form-grid-2">
                <div className="gov-form-group">
                  <label htmlFor="psec">Sector *</label>
                  <select
                    id="psec"
                    required
                    value={formData.sector}
                    onChange={(e) => setFormData({ ...formData, sector: e.target.value })}
                  >
                    {COMMON_SECTORS.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="gov-form-group">
                  <label htmlFor="pmin">Line Ministry *</label>
                  <input
                    id="pmin"
                    required
                    value={formData.ministry}
                    onChange={(e) => setFormData({ ...formData, ministry: e.target.value })}
                    placeholder="e.g. Ministry of Railways"
                  />
                </div>
              </div>

              <div className="gov-form-group">
                <label htmlFor="pagency">Implementing Agency *</label>
                <input
                  id="pagency"
                  required
                  value={formData.implementing_agency}
                  onChange={(e) => setFormData({ ...formData, implementing_agency: e.target.value })}
                  placeholder="e.g. NHAI, RVNL, NTPC"
                />
              </div>

              <div className="form-grid-2">
                <div className="gov-form-group">
                  <label htmlFor="pocost">Original Cost (₹ Crore) *</label>
                  <input
                    id="pocost"
                    type="number"
                    step="0.01"
                    min="1"
                    required
                    value={formData.original_cost_cr}
                    onChange={(e) => setFormData({ ...formData, original_cost_cr: parseFloat(e.target.value) || 0 })}
                  />
                </div>

                <div className="gov-form-group">
                  <label htmlFor="prcost">Revised Cost (₹ Crore)</label>
                  <input
                    id="prcost"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="Leave empty if unchanged"
                    value={formData.revised_cost_cr ?? ""}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        revised_cost_cr: e.target.value ? parseFloat(e.target.value) : null,
                      })
                    }
                  />
                </div>
              </div>

              <div className="form-grid-2">
                <div className="gov-form-group">
                  <label htmlFor="pexp">Cumulative Expenditure (₹ Crore)</label>
                  <input
                    id="pexp"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.expenditure_cr}
                    onChange={(e) => setFormData({ ...formData, expenditure_cr: parseFloat(e.target.value) || 0 })}
                  />
                </div>

                <div className="gov-form-group">
                  <label htmlFor="pprogress">Physical Progress (%)</label>
                  <input
                    id="pprogress"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={formData.physical_progress_pct}
                    onChange={(e) => setFormData({ ...formData, physical_progress_pct: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>

              <div className="form-grid-2">
                <div className="gov-form-group">
                  <label htmlFor="pdate-orig">Original Commissioning Date *</label>
                  <input
                    id="pdate-orig"
                    type="date"
                    required
                    value={formData.original_commissioning_date}
                    onChange={(e) => setFormData({ ...formData, original_commissioning_date: e.target.value })}
                  />
                </div>

                <div className="gov-form-group">
                  <label htmlFor="pdate-rev">Anticipated / Revised Date</label>
                  <input
                    id="pdate-rev"
                    type="date"
                    value={formData.revised_commissioning_date ?? ""}
                    onChange={(e) => setFormData({ ...formData, revised_commissioning_date: e.target.value || null })}
                  />
                </div>
              </div>
            </div>

            <div className="gov-modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <X size={16} /> Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={loading} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                {loading ? (
                  <>
                    <Clock size={16} className="spinner" /> Scoring & Registering…
                  </>
                ) : (
                  <>
                    <PlusCircle size={16} /> Register & Score Project
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
