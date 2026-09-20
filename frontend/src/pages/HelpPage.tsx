import { useEffect, useState } from "react";
import { LifeBuoy, Activity, MessageSquare, Keyboard, ShieldCheck } from "lucide-react";
import { API_URL, getJson, type Health } from "../api";

export default function HelpPage() {
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    getJson<Health>("/health").then(setHealth).catch(() => null);
  }, []);

  return (
    <section className="section faq" aria-labelledby="t">
      <div className="wrap">
        <div className="section-head">
          <p className="section-eyebrow">Help &amp; grievance</p>
          <h2 id="t" style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <LifeBuoy size={26} color="var(--navy-700)" /> Help, FAQs and support
          </h2>
          <p style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
            <Activity size={15} color="var(--teal)" /> Service status: <code>GET /health</code> → {health ? `${health.status} / DB ${health.database} / assistant ${health.assistant_enabled ? "enabled" : "disabled"}` : "checking…"} · API: {API_URL}
          </p>
        </div>
        <details open><summary>What does the overall score mean?</summary><p>A stored 0–100 summary of cost, time and implementation signals for one snapshot. Higher means higher stored exposure. See Dashboard for the current totals.</p></details>
        <details><summary>Why is a project marked unavailable?</summary><p>Revised costs, dates or model outputs were missing for that snapshot. Open the project detail page to see exactly which fields are missing.</p></details>
        <details><summary>Can the assistant change a prediction?</summary><p>No. <code>POST /assistant/query</code> only retrieves stored facts and model outputs, with caveats and source references.</p></details>
        <details><summary>How do I report a data issue?</summary><p>Quote the project code and dataset date (for example: ROAD-001 · 2026-09-13) so the dataset owner can trace the snapshot. Use the contact in the footer.</p></details>
        <div className="card-grid" style={{ marginTop: 16 }}>
          <article className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <MessageSquare size={18} color="var(--navy-700)" />
              <h3 style={{ margin: 0 }}>Contact support</h3>
            </div>
            <p>Access, data questions or accessibility assistance. Backend docs: <a className="link" href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">/docs</a>.</p>
          </article>
          <article className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <Keyboard size={18} color="var(--navy-700)" />
              <h3 style={{ margin: 0 }}>Keyboard help</h3>
            </div>
            <p>Tab to move · Enter to open · Esc to close dialogs. Text controls (A- / A / A+) are in the top bar.</p>
            <button className="btn btn-secondary btn-sm" type="button" onClick={() => document.documentElement.classList.toggle("high-contrast")}>Toggle high contrast</button>
          </article>
          <article className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <ShieldCheck size={18} color="var(--navy-700)" />
              <h3 style={{ margin: 0 }}>Authentication</h3>
            </div>
            <p>Admin upload uses <code>POST /auth/login</code> for a short-lived bearer token. Tokens are held in memory for this prototype.</p>
          </article>
        </div>
      </div>
    </section>
  );
}
