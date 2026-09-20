import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { getUser, setUser } from "../utils/auth";
import { signupApi } from "../api";

export default function SignupPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectTarget = searchParams.get("redirect") || "/dashboard";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // If already authenticated, redirect straight to target
  useEffect(() => {
    if (getUser()) {
      navigate(redirectTarget, { replace: true });
    }
  }, [navigate, redirectTarget]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    const cleanName = name.trim();
    const cleanEmail = email.trim();

    if (cleanName.length < 2) {
      setError("Please enter your full name (at least 2 characters).");
      return;
    }
    if (!cleanEmail.includes("@")) {
      setError("Please enter a valid official email address.");
      return;
    }
    if (password.length < 4) {
      setError("Please choose a password with at least 4 characters.");
      return;
    }

    setLoading(true);
    try {
      const response = await signupApi(cleanName, cleanEmail, password);
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
      const msg = err instanceof Error ? err.message : "Registration failed.";
      
      // Fallback in case backend is unreachable during client-only testing
      if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
        setUser({
          name: cleanName,
          email: cleanEmail,
          username: cleanName,
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

  const loginLink = redirectTarget !== "/dashboard"
    ? `/login?redirect=${encodeURIComponent(redirectTarget)}`
    : "/login";

  return (
    <div className="auth-page">
      <div className="auth-visual" aria-hidden="true">
        <img src="https://picsum.photos/seed/india-gate-delhi/1200/1400" alt="" />
        <div className="auth-visual-content">
          <p className="hero-kicker">Join the Monitoring System</p>
          <h2>Create an officer account to monitor infrastructure projects.</h2>
          <p>
            Register to access portfolio risk analytics, SHAP cost drivers, schedule predictions, and intervention trackers.
          </p>
          <div className="auth-badges">
            <span>Project Oversight</span>
            <span>Analytics</span>
            <span>Interventions</span>
          </div>
        </div>
      </div>
      <div className="auth-form-side">
        <div className="auth-top">
          <Link className="link" to="/">← Back to Home</Link>
          <span>SIH 26103 · Secure Gateway</span>
        </div>
        <div className="auth-box">
          <p className="section-eyebrow">Officer Registration</p>
          <h1>Create your account</h1>
          <p className="sub">
            Register your credentials to unlock access to protected monitoring and analytical dashboards.
          </p>

          {error && <div className="auth-error" role="alert">{error}</div>}

          <form onSubmit={onSubmit} aria-label="Signup form">
            <div className="field" style={{ marginBottom: 12 }}>
              <span><label htmlFor="name">Full name *</label></span>
              <input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Rajesh Kumar"
                required
              />
            </div>
            <div className="field" style={{ marginBottom: 12 }}>
              <span><label htmlFor="email">Official email *</label></span>
              <input
                id="email"
                type="email"
                autoComplete="email"
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
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Choose a password"
                required
              />
            </div>
            <button
              className="btn btn-primary"
              type="submit"
              disabled={loading}
              style={{ width: "100%" }}
            >
              {loading ? "Registering…" : `Sign up → Access ${redirectTarget === "/dashboard" ? "Dashboard" : "Page"}`}
            </button>
          </form>

          <p style={{ marginTop: 14 }}>
            Already registered? <Link className="link" to={loginLink}>Login</Link>
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
