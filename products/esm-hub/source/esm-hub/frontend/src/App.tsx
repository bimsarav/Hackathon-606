import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './lib/auth';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { IncidentList, IncidentNew } from './pages/Incidents';
import { IncidentDetail } from './pages/IncidentDetail';
import { ProblemList, ProblemDetail } from './pages/Problems';
import { Catalogue, RequestList, RequestDetail } from './pages/Requests';
import { Approvals } from './pages/Approvals';
import { ChangeList, ChangeDetail, ChangeCalendar, ChangeNew } from './pages/Changes';
import { AssetList, AssetDetail } from './pages/Assets';
import { KbList, KbArticle } from './pages/Knowledge';
import { Notifications } from './pages/Notifications';
import { Admin } from './pages/Admin';
import { Audit } from './pages/Audit';
import { Reports } from './pages/Reports';
import { Account } from './pages/Account';
import { hasRole, CONFIG_ROLES, REPORT_ROLES, R } from './lib/roles';

export function App() {
  const { user } = useAuth();
  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }
  return (
    <Routes>
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="incidents" element={<IncidentList />} />
        <Route path="incidents/new" element={<IncidentNew />} />
        <Route path="incidents/:id" element={<IncidentDetail />} />
        <Route path="problems" element={<ProblemList />} />
        <Route path="problems/:id" element={<ProblemDetail />} />
        <Route path="catalogue" element={<Catalogue />} />
        <Route path="requests" element={<RequestList />} />
        <Route path="requests/:id" element={<RequestDetail />} />
        <Route path="approvals" element={<Approvals />} />
        <Route path="changes" element={<ChangeList />} />
        <Route path="changes/calendar" element={<ChangeCalendar />} />
        <Route path="changes/new" element={<ChangeNew />} />
        <Route path="changes/:id" element={<ChangeDetail />} />
        <Route path="assets" element={<AssetList />} />
        <Route path="assets/:id" element={<AssetDetail />} />
        <Route path="knowledge" element={<KbList />} />
        <Route path="knowledge/:id" element={<KbArticle />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="account" element={<Account />} />
        <Route path="reports" element={hasRole(user, ...REPORT_ROLES) ? <Reports /> : <Navigate to="/" replace />} />
        <Route path="audit" element={hasRole(user, R.AUDITOR, R.ADMIN) ? <Audit /> : <Navigate to="/" replace />} />
        <Route path="admin/*" element={hasRole(user, ...CONFIG_ROLES) ? <Admin /> : <Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
