import { useEffect, useRef, useState, type FormEvent } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useCurrentUser } from "../utils/auth";
import { updateProfileApi } from "../api";


function adjustFont(direction: "down" | "reset" | "up") {
  const root = document.documentElement;
  const current = parseFloat(getComputedStyle(root).getPropertyValue("--font-scale")) || 1;
  const next = direction === "down" ? Math.max(0.875, current - 0.0625) : direction === "up" ? Math.min(1.25, current + 0.0625) : 1;
  root.style.setProperty("--font-scale", String(next));
}

type NavItem = { to: string; label: string; end?: boolean };
type Drop = { label: string; items: NavItem[] };

const TOP: (NavItem | Drop)[] = [
  { to: "/", label: "Home", end: true },
  { to: "/dashboard", label: "Dashboard" },
  {
    label: "Monitoring",
    items: [
      { to: "/monitoring", label: "Monitoring Overview" },
      { to: "/monitoring/changes", label: "Changes Since Last Snapshot" },
      { to: "/early-warnings", label: "Early Warnings" },
      { to: "/interventions", label: "Intervention Priority" },
      { to: "/risk/trends", label: "Risk Trends" },
    ],
  },
  { to: "/projects", label: "Projects" },
  {
    label: "Analytics",
    items: [
      { to: "/analytics", label: "Portfolio Analytics" },
      { to: "/analytics", label: "Sector Intelligence" },
      { to: "/analytics", label: "Ministry Intelligence" },
      { to: "/analytics", label: "Geographic Intelligence" },
      { to: "/analytics", label: "Cost Escalation Drivers" },
      { to: "/analytics", label: "Project Benchmarking" },
      { to: "/analytics/models", label: "Model Performance" },
    ],
  },
  { to: "/simulation", label: "Simulation" },
  { to: "/documents", label: "Documents" },
  { to: "/updates", label: "Updates" },
  { to: "/faq", label: "FAQ" },
  { to: "/help", label: "Help" },
];

function isDrop(x: NavItem | Drop): x is Drop { return "items" in x; }

export default function GovLayout() {
  const { user, updateUser, logout } = useCurrentUser();
  const navigate = useNavigate();
  const [mobileNav, setMobileNav] = useState(false);
  const [openDrop, setOpenDrop] = useState<string | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement | null>(null);

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editUsername, setEditUsername] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Close profile dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setProfileOpen(false);
      }
    }
    if (profileOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [profileOpen]);

  async function handleSaveProfile(e: FormEvent) {
    e.preventDefault();
    if (!editName.trim()) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      const updated = await updateProfileApi(
        editName.trim(),
        editUsername.trim() || editName.trim(),
        editEmail.trim() || undefined,
      );
      updateUser({
        name: updated.name,
        username: updated.username,
        email: updated.email,
        role: updated.role,
      });
      setSaveSuccess(true);
      setTimeout(() => {
        setSaveSuccess(false);
        setIsEditModalOpen(false);
      }, 700);
    } catch (err: any) {
      setSaveError(err?.message || "Failed to update profile. Please try again.");
    } finally {
      setIsSaving(false);
    }
  }

  const closeTimer = useRef<number | null>(null);
  const location = useLocation();
  const breadcrumbLabel = (() => {
    if (location.pathname.startsWith("/faq")) return "FAQ";
    if (location.pathname.startsWith("/updates")) return "Updates";
    if (location.pathname.startsWith("/monitoring")) return "Monitoring";
    if (location.pathname.startsWith("/early-warnings")) return "Early Warnings";
    if (location.pathname.startsWith("/interventions")) return "Interventions";
    if (location.pathname.startsWith("/risk/trends")) return "Risk Trends";
    if (location.pathname.startsWith("/analytics")) return "Analytics";
    if (location.pathname.startsWith("/simulation")) return "Simulation";
    if (location.pathname.startsWith("/projects/")) return "Project Detail";
    const flat = TOP.flatMap((t) => (isDrop(t) ? t.items : [t]));
    const hit = flat.find((r) => r.to !== "/" && location.pathname.startsWith(r.to));
    if (hit) return hit.label;
    if (location.pathname === "/") return "Home";
    return location.pathname.replace("/", "") || "Home";
  })();

  return (
    <div className="gov-shell">
      <a className="skip-link" href="#main-content">Skip to Main Content</a>
      <div className="utility-bar" role="region" aria-label="Accessibility tools">
        <div className="utility-inner">
          <div className="utility-left"><span className="gov-id">Smart India Hackathon 2026 · Prototype</span></div>
          <div className="utility-right">
            <a href="#main-content">Skip to Main Content</a><span className="utility-sep" aria-hidden="true">|</span>
            <button type="button" onClick={() => adjustFont("down")} aria-label="Decrease text size">A-</button>
            <button type="button" onClick={() => adjustFont("reset")} aria-label="Reset text size">A</button>
            <button type="button" onClick={() => adjustFont("up")} aria-label="Increase text size">A+</button>
            <span className="utility-sep" aria-hidden="true">|</span>
            <button type="button">हिन्दी</button><button type="button" aria-current="true">English</button>
            <span className="utility-sep hide-sm" aria-hidden="true">|</span>
            <button type="button" onClick={() => document.documentElement.classList.toggle("high-contrast")}>Accessibility</button>
            <a className="hide-sm" href="/faq">FAQ</a><a className="hide-sm" href="/help">Help</a><a className="hide-sm" href="#footer">Contact</a>
          </div>
        </div>
      </div>
      <header className="site-header">
        <div className="header-inner">
          <div className="brand"><div className="brand-emblem" aria-hidden="true">SIH<br />26103</div><div className="brand-text"><p className="brand-org">Government Digital Governance Prototype</p><p className="brand-title">Infrastructure Project Monitoring Portal</p><p className="brand-sub">SIH 26103 · Evidence-backed project oversight</p></div></div>
          <nav className="main-nav" aria-label="Primary">
            {TOP.map((item) =>
              isDrop(item) ? (
                <div
                  key={item.label}
                  className="nav-drop"
                  onMouseEnter={() => { if (closeTimer.current) window.clearTimeout(closeTimer.current); setOpenDrop(item.label); }}
                  onMouseLeave={() => { closeTimer.current = window.setTimeout(() => setOpenDrop(null), 180); }}
                  onFocus={() => setOpenDrop(item.label)}
                  onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setOpenDrop(null); }}
                >
                  <button
                    type="button"
                    className={`nav-drop-btn${openDrop === item.label ? " open" : ""}${item.items.some((i) => location.pathname.startsWith(i.to)) ? " active-parent" : ""}`}
                    aria-expanded={openDrop === item.label}
                    aria-haspopup="true"
                    onClick={() => setOpenDrop((v) => (v === item.label ? null : item.label))}
                    onKeyDown={(e) => { if (e.key === "Escape") setOpenDrop(null); }}
                  >
                    {item.label} <span aria-hidden="true" className="nav-caret">▾</span>
                  </button>
                  <div className={`nav-menu${openDrop === item.label ? " open" : ""}`} role="menu" onMouseEnter={() => { if (closeTimer.current) window.clearTimeout(closeTimer.current); }} onMouseLeave={() => { closeTimer.current = window.setTimeout(() => setOpenDrop(null), 180); }}>
                    {item.items.map((sub) => (
                      <NavLink key={`${item.label}-${sub.label}`} to={sub.to} role="menuitem" onClick={() => setOpenDrop(null)}>{sub.label}</NavLink>
                    ))}
                  </div>
                </div>
              ) : (
                <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => (isActive ? "active" : "")}>{item.label}</NavLink>
              )
            )}
          </nav>
          <div className="header-actions">
            <button className="btn btn-secondary btn-sm mobile-nav-toggle" type="button" onClick={() => setMobileNav((v) => !v)} aria-expanded={mobileNav} aria-label="Toggle navigation">Menu</button>
            {user ? (
              <div className="profile-dropdown-wrap" ref={profileRef}>
                <button
                  type="button"
                  className="profile-btn"
                  onClick={() => setProfileOpen((prev) => !prev)}
                  aria-expanded={profileOpen}
                  aria-haspopup="true"
                  aria-label="User profile and settings"
                >
                  <span className="profile-avatar-circle" aria-hidden="true">
                    {user.name ? user.name[0].toUpperCase() : (user.username ? user.username[0].toUpperCase() : "U")}
                  </span>
                  <span className="profile-name-text">{user.username || user.name}</span>
                  <span className="profile-caret" aria-hidden="true">▾</span>
                </button>
                {profileOpen && (
                  <div className="profile-menu" role="menu">
                    <div className="profile-menu-info">
                      <div className="profile-menu-name">{user.name}</div>
                      <div className="profile-menu-email">{user.email}</div>
                    </div>
                    <div className="profile-menu-divider" />
                    <button
                      type="button"
                      className="profile-menu-action"
                      role="menuitem"
                      onClick={() => {
                        setEditName(user.name);
                        setEditUsername(user.username || user.name);
                        setEditEmail(user.email);
                        setSaveSuccess(false);
                        setSaveError(null);
                        setProfileOpen(false);
                        setIsEditModalOpen(true);
                      }}
                    >
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                      </svg>
                      Edit Profile
                    </button>
                    <button
                      type="button"
                      className="profile-menu-action profile-menu-signout"
                      role="menuitem"
                      onClick={() => {
                        setProfileOpen(false);
                        logout();
                        navigate("/");
                      }}
                    >
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                        <polyline points="16 17 21 12 16 7" />
                        <line x1="21" y1="12" x2="9" y2="12" />
                      </svg>
                      Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <>
                <NavLink className="btn btn-secondary btn-sm" to="/login">Login</NavLink>
                <NavLink className="btn btn-primary btn-sm" to="/signup">Sign Up</NavLink>
              </>
            )}
          </div>
        </div>
        <div className="nav-rule" aria-hidden="true" />
        {mobileNav && (
          <nav className="mobile-nav" aria-label="Mobile">
            <NavLink to="/" end onClick={() => setMobileNav(false)}>Home</NavLink>
            <NavLink to="/dashboard" onClick={() => setMobileNav(false)}>Dashboard</NavLink>
            <div className="mobile-group"><span className="mobile-label">Monitoring</span>
              <NavLink to="/monitoring" onClick={() => setMobileNav(false)}>Monitoring Overview</NavLink>
              <NavLink to="/monitoring/changes" onClick={() => setMobileNav(false)}>Changes Since Last Snapshot</NavLink>
              <NavLink to="/early-warnings" onClick={() => setMobileNav(false)}>Early Warnings</NavLink>
              <NavLink to="/interventions" onClick={() => setMobileNav(false)}>Intervention Priority</NavLink>
              <NavLink to="/risk/trends" onClick={() => setMobileNav(false)}>Risk Trends</NavLink>
            </div>
            <NavLink to="/projects" onClick={() => setMobileNav(false)}>Projects</NavLink>
            <div className="mobile-group"><span className="mobile-label">Analytics</span>
              <NavLink to="/analytics" onClick={() => setMobileNav(false)}>Portfolio Analytics</NavLink>
              <NavLink to="/analytics" onClick={() => setMobileNav(false)}>Sector Intelligence</NavLink>
              <NavLink to="/analytics" onClick={() => setMobileNav(false)}>Ministry Intelligence</NavLink>
              <NavLink to="/analytics" onClick={() => setMobileNav(false)}>Geographic Intelligence</NavLink>
              <NavLink to="/analytics" onClick={() => setMobileNav(false)}>Cost Escalation Drivers</NavLink>
              <NavLink to="/analytics" onClick={() => setMobileNav(false)}>Project Benchmarking</NavLink>
              <NavLink to="/analytics/models" onClick={() => setMobileNav(false)}>Model Performance</NavLink>
            </div>
            <NavLink to="/simulation" onClick={() => setMobileNav(false)}>Simulation</NavLink>
            <NavLink to="/documents" onClick={() => setMobileNav(false)}>Documents</NavLink>
            <NavLink to="/updates" onClick={() => setMobileNav(false)}>Updates</NavLink>
            <NavLink to="/faq" onClick={() => setMobileNav(false)}>FAQ</NavLink>
            <NavLink to="/help" onClick={() => setMobileNav(false)}>Help</NavLink>
            <div className="mobile-actions">
              {user ? (
                <div className="mobile-profile-box">
                  <div className="mobile-profile-user">
                    <span className="profile-avatar-circle" aria-hidden="true">
                      {user.name ? user.name[0].toUpperCase() : "U"}
                    </span>
                    <div className="mobile-profile-details">
                      <div className="mobile-profile-name">{user.username || user.name}</div>
                      <div className="mobile-profile-email">{user.email}</div>
                    </div>
                  </div>
                  <div className="mobile-profile-buttons">
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => {
                        setEditName(user.name);
                        setEditUsername(user.username || user.name);
                        setEditEmail(user.email);
                        setMobileNav(false);
                        setIsEditModalOpen(true);
                      }}
                    >
                      Edit Profile
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => {
                        setMobileNav(false);
                        logout();
                        navigate("/");
                      }}
                    >
                      Sign Out
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <NavLink to="/login" onClick={() => setMobileNav(false)}>Login</NavLink>
                  <NavLink to="/signup" onClick={() => setMobileNav(false)}>Sign Up</NavLink>
                </>
              )}
            </div>
          </nav>
        )}
      </header>
      <main className="page" id="main-content">
        <div className="wrap"><nav className="breadcrumb" aria-label="Breadcrumb"><ol><li><NavLink to="/">Home</NavLink></li><li aria-hidden="true">›</li><li aria-current="page">{breadcrumbLabel}</li></ol></nav></div>
        <Outlet />
      </main>
      <footer className="site-footer" id="footer">
        <div className="wrap">
          <div className="footer-grid"><div><h2>Infrastructure Project Monitoring Portal</h2><p>SIH 26103 Prototype</p><p>“This prototype demonstrates digital monitoring, risk visibility and evidence-based decision support.”</p><p className="footer-teal">Prototype — not an official Government of India website.</p></div><nav aria-label="Platform"><h3>Platform</h3><ul><li><NavLink to="/">Home</NavLink></li><li><NavLink to="/dashboard">Dashboard</NavLink></li><li><NavLink to="/projects">Projects</NavLink></li><li><NavLink to="/analytics">Analytics</NavLink></li><li><NavLink to="/documents">Documents</NavLink></li></ul></nav><nav aria-label="Information"><h3>Information</h3><ul><li><NavLink to="/help">Accessibility</NavLink></li><li><NavLink to="/faq">FAQs</NavLink></li><li><NavLink to="/help">Help</NavLink></li><li><a href="#footer">Contact</a></li><li><NavLink to="/documents">Sitemap</NavLink></li></ul></nav><nav aria-label="Policies"><h3>Policies</h3><ul><li><NavLink to="/help">Privacy</NavLink></li><li><NavLink to="/help">Terms of Use</NavLink></li><li><NavLink to="/help">Accessibility Statement</NavLink></li><li><NavLink to="/help">Data Policy</NavLink></li></ul></nav></div>
          <div className="footer-bottom"><span>© 2026 SIH 26103 Prototype · For demonstration purposes only · Last Updated: 14 September 2026</span><span>English / हिन्दी ready · No certification claimed</span></div>
        </div>
      </footer>
      {isEditModalOpen && (
        <div className="profile-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="edit-profile-title" onClick={() => setIsEditModalOpen(false)}>
          <div className="profile-modal" onClick={(e) => e.stopPropagation()}>
            <div className="profile-modal-header">
              <div>
                <h3 id="edit-profile-title" style={{ margin: 0, fontSize: "1.05rem", color: "var(--navy-900)" }}>Edit Profile</h3>
                <p style={{ margin: "2px 0 0", fontSize: "0.8rem", color: "var(--ink-2)" }}>Update your account details</p>
              </div>
              <button
                type="button"
                className="profile-modal-close"
                onClick={() => setIsEditModalOpen(false)}
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleSaveProfile}>
              <div className="profile-modal-body">
                {saveSuccess && (
                  <div className="alert alert-info" style={{ padding: "8px 12px", margin: 0, fontSize: "0.85rem" }}>
                    ✓ Profile updated successfully!
                  </div>
                )}
                {saveError && (
                  <div className="alert" style={{ padding: "8px 12px", margin: 0, fontSize: "0.85rem", color: "#991B1B", background: "#FEE2E2", border: "1px solid #F87171", borderRadius: "4px" }}>
                    {saveError}
                  </div>
                )}
                <div className="field">
                  <span><label htmlFor="edit-name">Full Name *</label></span>
                  <input
                    id="edit-name"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    placeholder="Enter your name"
                    required
                    disabled={isSaving}
                  />
                </div>
                <div className="field">
                  <span><label htmlFor="edit-username">Display Username</label></span>
                  <input
                    id="edit-username"
                    value={editUsername}
                    onChange={(e) => setEditUsername(e.target.value)}
                    placeholder="Enter username"
                    disabled={isSaving}
                  />
                </div>
                <div className="field">
                  <span><label htmlFor="edit-email">Official Email</label></span>
                  <input
                    id="edit-email"
                    type="email"
                    value={editEmail}
                    onChange={(e) => setEditEmail(e.target.value)}
                    placeholder="name@department.gov.in"
                    disabled={isSaving}
                  />
                </div>
              </div>
              <div className="profile-modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setIsEditModalOpen(false)}
                  disabled={isSaving}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary btn-sm" disabled={isSaving}>
                  {isSaving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
