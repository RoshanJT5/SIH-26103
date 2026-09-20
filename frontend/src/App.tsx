import { BrowserRouter, Route, Routes } from "react-router-dom";
import GovLayout from "./layout/GovLayout";
import ProtectedRoute from "./components/ProtectedRoute";
import Home from "./pages/Home";
import DashboardPage from "./pages/DashboardPage";
import ProjectsPage from "./pages/ProjectsPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import DocumentsPage from "./pages/DocumentsPage";
import HelpPage from "./pages/HelpPage";
import FaqPage from "./pages/FaqPage";
import ChangesPage from "./pages/ChangesPage";
import EarlyWarningsPage from "./pages/EarlyWarningsPage";
import InterventionsPage from "./pages/InterventionsPage";
import SimulationPage from "./pages/SimulationPage";
import ModelsPage from "./pages/ModelsPage";
import MonitoringOverview from "./pages/MonitoringOverview";
import TrendsPage from "./pages/TrendsPage";
import UpdatesPage from "./pages/UpdatesPage";
import UpdateDetailPage from "./pages/UpdateDetailPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public authentication pages */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        {/* Application Layout */}
        <Route element={<GovLayout />}>
          {/* Public Pages: Accessible without authentication */}
          <Route index element={<Home />} />
          <Route path="help" element={<HelpPage />} />
          <Route path="faq" element={<FaqPage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="updates" element={<UpdatesPage />} />
          <Route path="updates/:id" element={<UpdateDetailPage />} />

          {/* Protected Pages: Authentication required (unauthenticated visitors redirect to /login) */}
          <Route element={<ProtectedRoute />}>
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="monitoring" element={<MonitoringOverview />} />
            <Route path="monitoring/changes" element={<ChangesPage />} />
            <Route path="early-warnings" element={<EarlyWarningsPage />} />
            <Route path="interventions" element={<InterventionsPage />} />
            <Route path="risk/trends" element={<TrendsPage />} />
            <Route path="simulation" element={<SimulationPage />} />
            <Route path="projects" element={<ProjectsPage />} />
            <Route path="projects/:id" element={<ProjectDetailPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="analytics/models" element={<ModelsPage />} />
          </Route>

          {/* 404 Fallback */}
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

function NotFound() {
  return (
    <section className="section">
      <div className="wrap">
        <div className="section-head">
          <p className="section-eyebrow">404</p>
          <h2>Page not found</h2>
          <p>The page you requested does not exist or has been moved.</p>
        </div>
      </div>
    </section>
  );
}
