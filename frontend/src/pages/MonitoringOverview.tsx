import { Link } from "react-router-dom";

export default function MonitoringOverview() {
  return (
    <section className="section">
      <div className="wrap">
        <div className="section-head"><p className="section-eyebrow">Monitoring</p><h1 style={{ color: "#0D3157", margin: "6px 0" }}>Monitoring Overview</h1><p>Central place for snapshot comparison, early warnings, intervention priority and risk trends.</p></div>
        <div className="card-grid">
          <article className="card"><h3>Changes Since Last Snapshot</h3><p>Compare the current completed dataset against the previous one.</p><Link className="link" to="/monitoring/changes">Open Changes →</Link></article>
          <article className="card"><h3>Early Warnings</h3><p>Risk escalation and progress-deviation signals requiring review.</p><Link className="link" to="/early-warnings">Open Early Warnings →</Link></article>
          <article className="card"><h3>Intervention Priority</h3><p>Which projects should be looked at first, with transparent drivers.</p><Link className="link" to="/interventions">Open Priority →</Link></article>
        </div>
        <p style={{ marginTop: 16 }}><Link className="link" to="/risk/trends">View Risk Trends →</Link></p>
      </div>
    </section>
  );
}
