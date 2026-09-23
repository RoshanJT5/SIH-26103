import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  ArrowRight,
  HelpCircle,
  LogIn,
  UserPlus,
  FileText,
  LifeBuoy,
} from "lucide-react";

export default function FaqPage() {
  const [filter, setFilter] = useState("");

  const faqs = [
    {
      category: "Access & Security",
      q: "Which pages require authentication to access?",
      a: "Pages containing detailed operational metrics, early warnings, predictive machine learning models, and intervention management (such as Dashboard, Monitoring, Early Warnings, Simulation, Projects, and Analytics) require official authentication. Public visitors can freely access the Landing Page, FAQs, Help Center, Public Documents, and Official Updates.",
    },
    {
      category: "Access & Security",
      q: "How do I gain access to the Project Monitoring Dashboard?",
      a: "Government nodal officers, project directors, and authorized department personnel can register via the Sign Up page using their official email or sign in directly with their credentials. Once authenticated, you will immediately be directed to your dashboard or requested monitoring page.",
    },
    {
      category: "Access & Security",
      q: "What happens if I try to visit a protected page while logged out?",
      a: "You will be automatically redirected to the secure Login page. Once you sign in or create an account, the system will seamlessly forward you directly to the page you originally requested.",
    },
    {
      category: "Methodology & Scoring",
      q: "What does the Overall Risk Score indicate?",
      a: "The Overall Score is an empirical, evidence-based composite rating (0–100) combining schedule revision days, cost escalation ratios, physical progress velocity, and machine learning risk probabilities. A higher score reflects higher project exposure requiring immediate monitoring attention.",
    },
    {
      category: "Methodology & Scoring",
      q: "What are the four Risk Bands?",
      a: "Projects are categorized into four standardized bands: Low Risk (Green, score < 25), Medium Risk (Amber, score 25–49), High Risk (Orange, score 50–74), and Critical Exposure (Red, score ≥ 75).",
    },
    {
      category: "Data & Transparency",
      q: "What information is publicly accessible without logging in?",
      a: "Citizens, researchers, and media can view high-level public portal statistics, national policy guidelines, published monthly project updates and bulletins, grievance contacts, and this FAQ repository without logging in.",
    },
    {
      category: "Technical Support",
      q: "Who should I contact if I encounter difficulties logging in?",
      a: "You can consult the Help section or reach out to the nodal technical support desk. If you have departmental credentials, verify that you are entering your official registered email and matching password.",
    },
  ];

  const filteredFaqs = filter.trim()
    ? faqs.filter(
        (f) =>
          f.q.toLowerCase().includes(filter.toLowerCase()) ||
          f.a.toLowerCase().includes(filter.toLowerCase()) ||
          f.category.toLowerCase().includes(filter.toLowerCase())
      )
    : faqs;

  return (
    <section className="section faq-page" aria-labelledby="faq-title">
      <div className="wrap">
        <div className="section-head">
          <p className="section-eyebrow">Public Information</p>
          <h1 id="faq-title" style={{ fontSize: "2rem", marginBottom: "8px", display: "flex", alignItems: "center", gap: 8 }}>
            <HelpCircle size={28} color="var(--navy-700)" /> Frequently Asked Questions (FAQ)
          </h1>
          <p className="sub" style={{ maxWidth: 720 }}>
            Learn about access policies, public versus protected areas, data methodologies,
            and monitoring tools for SameekshaSetu (Infrastructure Project Monitoring Portal).
          </p>
        </div>

        <div style={{ margin: "20px 0 28px", maxWidth: 480 }}>
          <div className="field">
            <span>
              <label htmlFor="faq-search" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <Search size={13} /> Search questions
              </label>
            </span>
            <input
              id="faq-search"
              type="search"
              placeholder="Search by topic, e.g. login, dashboard, score..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>
        </div>

        <div className="faq-list" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {filteredFaqs.length === 0 ? (
            <div className="card" style={{ padding: 24, textAlign: "center" }}>
              <p>No questions matched your search “{filter}”.</p>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setFilter("")}
                style={{ marginTop: 8 }}
              >
                Clear Search
              </button>
            </div>
          ) : (
            filteredFaqs.map((faq, idx) => (
              <details
                key={faq.q}
                open={idx === 0}
                style={{
                  background: "var(--card-bg, #ffffff)",
                  border: "1px solid var(--border-color, #e2e8f0)",
                  borderRadius: 8,
                  padding: "14px 18px",
                }}
              >
                <summary style={{ fontWeight: 600, cursor: "pointer", fontSize: "1.05rem" }}>
                  <span
                    style={{
                      fontSize: "0.75rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      color: "var(--ink-2, #64748b)",
                      marginRight: 10,
                    }}
                  >
                    [{faq.category}]
                  </span>
                  {faq.q}
                </summary>
                <p style={{ marginTop: 10, lineHeight: 1.6, color: "var(--ink-1, #1e293b)" }}>
                  {faq.a}
                </p>
              </details>
            ))
          )}
        </div>

        <div className="card-grid" style={{ marginTop: 36 }}>
          <article className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <LogIn size={20} color="var(--navy-700)" />
              <h3 style={{ margin: 0 }}>Need Access?</h3>
            </div>
            <p>Authorized officials can register or log in to access the active monitoring dashboard and predictive insights.</p>
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <Link className="btn btn-primary btn-sm" to="/login" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <LogIn size={13} /> Official Login
              </Link>
              <Link className="btn btn-secondary btn-sm" to="/signup" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <UserPlus size={13} /> Register
              </Link>
            </div>
          </article>
          <article className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <FileText size={20} color="var(--navy-700)" />
              <h3 style={{ margin: 0 }}>Public Documents</h3>
            </div>
            <p>Download open oversight reports, guidelines, data dictionary formats, and standard operating procedures.</p>
            <Link className="link" to="/documents" style={{ display: "inline-flex", alignItems: "center", gap: 3, marginTop: 12 }}>
              Browse Documents <ArrowRight size={13} />
            </Link>
          </article>
          <article className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <LifeBuoy size={20} color="var(--navy-700)" />
              <h3 style={{ margin: 0 }}>Help &amp; Grievance</h3>
            </div>
            <p>Check system health, accessibility guidelines, keyboard shortcuts, or submit feedback.</p>
            <Link className="link" to="/help" style={{ display: "inline-flex", alignItems: "center", gap: 3, marginTop: 12 }}>
              Go to Help Center <ArrowRight size={13} />
            </Link>
          </article>
        </div>
      </div>
    </section>
  );
}
