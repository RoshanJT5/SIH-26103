import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { getUser, setUser } from "../utils/auth";
import { loginApi } from "../api";

export default function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectTarget = searchParams.get("redirect") || "/dashboard";
  const reason = searchParams.get("reason");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // If already authenticated, forward immediately to destination or dashboard
  useEffect(() => {
    if (getUser()) {
      navigate(redirectTarget, { replace: true });
    }
  }, [navigate, redirectTarget]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    const cleanEmail = email.trim();
    if (!cleanEmail.includes("@")) {
      setError("Please enter a valid official email address.");
      return;
    }
    if (password.length < 4) {
      setError("Password must be at least 4 characters long.");
      return;
    }

    setLoading(true);
    try {
      // 1. Try real backend authentication
      const response = await loginApi(cleanEmail, password);
      setUser(
        {
          name: response.user.name,
          email: response.user.email,
          username: response.user.username,
          role: response.user.role || "officer",
        },
        response.access_token
      );
      navigate(redirectTarget, { replace: true });
    } catch (err: unknown) {
      // If server returned a clear message (e.g. invalid credentials)
      const msg = err instanceof Error ? err.message : "Authentication failed.";
      
      // If backend was unreachable or network failure, provide fallback for prototype demo
      if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
        const existing = getUser();
        const fallbackName = cleanEmail.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        const name = existing && existing.email.toLowerCase() === cleanEmail.toLowerCase() ? existing.name : fallbackName;
        setUser({
          name,
          email: cleanEmail,
          username: name,
          role: "officer",
        });
        navigate(redirectTarget, { replace: true });
        return;
      }
      
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  const signupLink = redirectTarget !== "/dashboard"
    ? `/signup?redirect=${encodeURIComponent(redirectTarget)}`
    : "/signup";

  return (
    <div className="auth-page">
      <div className="auth-visual" aria-hidden="true">
        <img src="https://picsum.photos/seed/india-parliament-house/1200/1400" alt="" />
        <div className="auth-visual-content">
          <p className="hero-kicker">Official Portal Access</p>
          <h2>Secure access to the infrastructure project monitoring portal.</h2>
          <p>
            Detailed project risk indicators, ML predictions, and intervention management require authenticated officer credentials.
          </p>
          <div className="auth-badges">
            <span>Verified Nodal Officer</span>
            <span>Risk Visibility</span>
            <span>Audit Trail</span>
          </div>
        </div>
      </div>
      <div className="auth-form-side">
        <div className="auth-top">
          <Link className="link" to="/">← Back to Home</Link>
          <span>SIH 26103 · Secure Gateway</span>
        </div>
        <div className="auth-box">
          <p className="section-eyebrow">Officer Sign In</p>
          <h1>Login to your account</h1>
          <p className="sub">
            Access protected monitoring dashboards, early warnings, and analytical forecasting.
          </p>

          {reason === "auth_required" && !error && (
            <div
              className="alert alert-info"
              style={{
                marginBottom: 16,
                padding: "10px 14px",
                borderRadius: 6,
                fontSize: "0.85rem",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
              role="status"
            >
              <span aria-hidden="true">🔒</span>
              <div>
                <strong>Authentication Required:</strong> Please log in or register to view {redirectTarget.replace("/", "").replace(/-/g, " ") || "the requested page"}.
              </div>
            </div>
          )}

          {error && <div className="auth-error" role="alert">{error}</div>}

          <form onSubmit={onSubmit} aria-label="Login form">
            <div className="field" style={{ marginBottom: 12 }}>
              <span><label htmlFor="email">Official email *</label></span>
              <input
                id="email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@department.gov.in"
                required
              />
            </div>
            <div className="field" style={{ marginBottom: 16 }}>
              <span><label htmlFor="password">Password *</label></span>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
            <button
              className="btn btn-primary"
              type="submit"
              disabled={loading}
              style={{ width: "100%" }}
            >
              {loading ? "Authenticating…" : `Login → Access ${redirectTarget === "/dashboard" ? "Dashboard" : "Page"}`}
            </button>
          </form>

          <p style={{ marginTop: 14 }}>
            New officer or team member? <Link className="link" to={signupLink}>Create an account</Link>
          </p>

          <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--border-color, #e2e8f0)", fontSize: "0.8rem", color: "var(--ink-2)" }}>
            <p style={{ margin: 0 }}>
              Need public information? Visit the <Link className="link" to="/">Landing Page</Link>, <Link className="link" to="/faq">FAQs</Link>, or <Link className="link" to="/help">Help Center</Link>.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
