import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { setUser } from "../utils/auth";

export default function SignupPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (name.trim().length < 2) { setError("Enter your full name."); return; }
    if (!email.includes("@")) { setError("Enter a valid email address."); return; }
    if (password.length < 4) { setError("Choose a password of at least 4 characters for this prototype."); return; }
    setUser({
      name: name.trim(),
      email: email.trim(),
      username: name.trim(),
    });
    navigate("/dashboard", { replace: true });
  }

  return (
    <div className="auth-page">
      <div className="auth-visual" aria-hidden="true">
        <img src="https://picsum.photos/seed/india-gate-delhi/1200/1400" alt="" />
        <div className="auth-visual-content">
          <p className="hero-kicker">Join the Prototype</p>
          <h2>Create an account to explore the monitoring portal.</h2>
          <p>Create your profile to access real-time project risk monitoring, forecasting, and analytics.</p>
          <div className="auth-badges"><span>Dashboard</span><span>Analytics</span><span>Documents</span></div>
        </div>
      </div>
      <div className="auth-form-side">
        <div className="auth-top"><Link className="link" to="/">← Back to Home</Link><span>SIH 26103 · Prototype</span></div>
        <div className="auth-box">
          <p className="section-eyebrow">Register</p>
          <h1>Create your account</h1>
          <p className="sub">No backend account is created — details stay in this browser for the demo.</p>
          {error && <div className="auth-error" role="alert">{error}</div>}
          <form onSubmit={onSubmit} aria-label="Signup form">
            <div className="field" style={{ marginBottom: 12 }}><span><label htmlFor="name">Full name *</label></span><input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Enter your name" required /></div>
            <div className="field" style={{ marginBottom: 12 }}><span><label htmlFor="email">Email *</label></span><input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@department.gov.in" required /></div>
            <div className="field" style={{ marginBottom: 16 }}><span><label htmlFor="password">Password *</label></span><input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Choose a password" required /></div>
            <button className="btn btn-primary" type="submit" style={{ width: "100%" }}>Sign up → Dashboard</button>
          </form>
          <p style={{ marginTop: 14 }}>Already registered? <Link className="link" to="/login">Login</Link></p>
        </div>
      </div>
    </div>
  );
}
