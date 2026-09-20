import React, { useState } from "react";
import { uploadDatasetApi } from "../api";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onUploaded?: (data: any) => void;
}

export default function UploadDatasetModal({ isOpen, onClose, onUploaded }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [sourceDate, setSourceDate] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a CSV file to upload.");
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const res = await uploadDatasetApi(file, sourceDate || undefined);
      setResult(res);
      if (onUploaded) onUploaded(res);
    } catch (err: any) {
      setError(err?.message || "Failed to upload and validate CSV dataset.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="gov-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="upload-modal-title">
      <div className="gov-modal">
        <div className="gov-modal-header">
          <div>
            <h3 id="upload-modal-title">Ingest MoSPI Project Dataset</h3>
            <p>Upload official CSV flash report to update the monitoring baseline and re-run models</p>
          </div>
          <button type="button" className="gov-modal-close" onClick={onClose} aria-label="Close dialog">
            ✕
          </button>
        </div>

        {result ? (
          <div className="gov-modal-body">
            <div style={{ textAlign: "center", padding: "16px 8px" }}>
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: "50%",
                  background: "#E6F4EA",
                  color: "#137333",
                  display: "grid",
                  placeItems: "center",
                  fontSize: 26,
                  margin: "0 auto 12px",
                }}
              >
                ✓
              </div>
              <h4 style={{ margin: "0 0 6px", color: "var(--navy-900)", fontSize: "1.15rem" }}>
                Dataset Ingested & Scored!
              </h4>
              <p style={{ margin: "0 0 16px", color: "var(--ink-2)", fontSize: "0.88rem" }}>
                Source: <strong>{result.filename}</strong>
              </p>

              <div
                style={{
                  display: "flex",
                  justifyContent: "center",
                  gap: 16,
                  margin: "16px 0",
                  flexWrap: "wrap",
                }}
              >
                <div style={{ background: "var(--bg-alt)", padding: "10px 16px", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: "0.72rem", color: "var(--ink-3)", textTransform: "uppercase" }}>Accepted Records</div>
                  <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--navy-900)" }}>
                    {result.accepted_count}
                  </div>
                </div>
                <div style={{ background: "var(--bg-alt)", padding: "10px 16px", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: "0.72rem", color: "var(--ink-3)", textTransform: "uppercase" }}>Rejected / Issues</div>
                  <div style={{ fontSize: "1.3rem", fontWeight: 700, color: result.rejected_count > 0 ? "var(--error)" : "var(--success)" }}>
                    {result.rejected_count}
                  </div>
                </div>
              </div>
              <p style={{ fontSize: "0.82rem", color: "var(--ink-3)" }}>
                ML risk pipelines and early warning detection rules have processed all imported projects.
              </p>
            </div>

            <div className="gov-modal-footer">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  onClose();
                  window.location.reload();
                }}
              >
                Refresh Dashboard & Portfolio
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="gov-modal-body">
              {error && (
                <div className="alert alert-error" role="alert">
                  {error}
                </div>
              )}

              <div className="notice info" style={{ padding: "10px 14px", borderRadius: 6, fontSize: "0.82rem" }}>
                <strong>MoSPI Format Requirement:</strong> Supports official MoSPI flash report format (.csv) containing project codes, sectors, sanction costs, cumulative expenditure, and commissioning dates.
              </div>

              <div className="gov-form-group">
                <label htmlFor="csv-file">Select CSV File *</label>
                <input
                  id="csv-file"
                  type="file"
                  accept=".csv"
                  required
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  style={{ padding: "8px" }}
                />
                <span className="form-hint">Maximum upload file size: 10 MB</span>
              </div>

              <div className="gov-form-group">
                <label htmlFor="csv-date">Report As-Of Date (Optional)</label>
                <input
                  id="csv-date"
                  type="date"
                  value={sourceDate}
                  onChange={(e) => setSourceDate(e.target.value)}
                />
                <span className="form-hint">Reference date for historical snapshot comparison</span>
              </div>
            </div>

            <div className="gov-modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={loading || !file}>
                {loading ? "Validating & Ingesting…" : "Upload & Analyze"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
