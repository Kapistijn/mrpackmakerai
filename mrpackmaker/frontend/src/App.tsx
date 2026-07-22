import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import NewProject from './pages/NewProject';
import ProjectBuilder from './pages/ProjectBuilder';
import Settings from './pages/Settings';
import ApiSettings from './pages/ApiSettings';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/new" element={<NewProject />} />
        <Route path="/project/:id" element={<ProjectBuilder />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/settings/api" element={<ApiSettings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

export default App;
