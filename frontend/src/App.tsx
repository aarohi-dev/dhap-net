import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Overview from './pages/Overview';
import LiveMonitoring from './pages/LiveMonitoring';
import AttackGraph from './pages/AttackGraph';
import Predictions from './pages/Predictions';
import AnomalyDetection from './pages/AnomalyDetection';
import EntityInvestigation from './pages/EntityInvestigation';
import Analytics from './pages/Analytics';
import Reports from './pages/Reports';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/overview" replace />} />
          <Route path="overview" element={<Overview />} />
          <Route path="monitoring" element={<LiveMonitoring />} />
          <Route path="graph" element={<AttackGraph />} />
          <Route path="predictions" element={<Predictions />} />
          <Route path="anomalies" element={<AnomalyDetection />} />
          <Route path="entities" element={<EntityInvestigation />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="reports" element={<Reports />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
