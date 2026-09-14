import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email.includes("@")) { setError("Enter a valid official email address."); return; }
    if (password.length < 4) { setError("Enter your password (minimum 4 characters for this prototype)."); return; }
    sessionStorage.setItem("sih-auth", JSON.stringify({ email }));
    navigate("/dashboard", { replace: true });
  }

  return (
    <div className="auth-page">
      <div className="auth-visual" aria-hidden="true">
        <img src="https://picsum.photos/seed/india-parliament-house/1200/1400" alt="" />
        <div className="auth-visual-content">
          <p className="hero-kicker">Official Prototype Access</p>
          <h2>Secure access to the project monitoring dashboard.</h2>
          <p>Prototype authentication only — no real credentials are verified. After login you are routed to the dashboard.</p>
          <div className="auth-badges"><span>Snapshot Data</span><span>Role Access</span><span>Audit Ready</span></div>
        </div>
      </div>
      <div className="auth-form-side">
        <div className="auth-top"><Link className="link" to="/">← Back to Home</Link><span>SIH 26103 · Prototype</span></div>
        <div className="auth-box">
          <p className="section-eyebrow">Secure Login</p>
          <h1>Login to your account</h1>
          <p className="sub">Your session stays in this browser only. No backend account is created.</p>
          {error && <div className="auth-error" role="alert">{error}</div>}
          <form onSubmit={onSubmit} aria-label="Login form">
            <div className="field" style={{ marginBottom: 12 }}><span><label htmlFor="email">Official email *</label></span><input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@department.gov.in" required /></div>
            <div className="field" style={{ marginBottom: 16 }}><span><label htmlFor="password">Password *</label></span><input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required /></div>
            <button className="btn btn-primary" type="submit" style={{ width: "100%" }}>Login → Dashboard</button>
          </form>
          <p style={{ marginTop: 14 }}>New here? <Link className="link" to="/signup">Create an account</Link></p>
        </div>
      </div>
    </div>
  );
}
