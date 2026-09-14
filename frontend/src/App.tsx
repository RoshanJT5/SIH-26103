import { BrowserRouter, Route, Routes } from "react-router-dom";
import GovLayout from "./layout/GovLayout";
import Home from "./pages/Home";
import DashboardPage from "./pages/DashboardPage";
import ProjectsPage from "./pages/ProjectsPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import DocumentsPage from "./pages/DocumentsPage";
import HelpPage from "./pages/HelpPage";
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
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route element={<GovLayout />}>
          <Route index element={<Home />} />
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
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="updates" element={<UpdatesPage />} />
          <Route path="updates/:id" element={<UpdateDetailPage />} />
          <Route path="help" element={<HelpPage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
function NotFound() {
  return (<section className="section"><div className="wrap"><div className="section-head"><p className="section-eyebrow">404</p><h2>Page not found</h2><p>The page you asked for does not exist.</p></div></div></section>);
}
