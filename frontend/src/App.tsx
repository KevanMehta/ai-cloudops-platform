import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import CostAnalytics from './pages/CostAnalytics';
import Anomalies from './pages/Anomalies';
import AgentReport from './pages/AgentReport';
import TerraformAnalyzer from './pages/TerraformAnalyzer';
import KubernetesHealth from './pages/KubernetesHealth';
import Recommendations from './pages/Recommendations';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="costs" element={<CostAnalytics />} />
          <Route path="anomalies" element={<Anomalies />} />
          <Route path="agent" element={<AgentReport />} />
          <Route path="terraform" element={<TerraformAnalyzer />} />
          <Route path="kubernetes" element={<KubernetesHealth />} />
          <Route path="recommendations" element={<Recommendations />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
