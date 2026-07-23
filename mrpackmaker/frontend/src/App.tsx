import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import NewProject from './pages/NewProject';
import ProjectBuilder from './pages/ProjectBuilder';
import AdvancedSettings from './pages/AdvancedSettings';
import Settings from './pages/Settings';
import ApiSettings from './pages/ApiSettings';
import AIEditor from './pages/AIEditor';
function App(){return <Layout><Routes><Route path="/" element={<Dashboard/>}/><Route path="/new" element={<NewProject/>}/><Route path="/project/:id" element={<ProjectBuilder/>}/><Route path="/project/:id/editor" element={<AIEditor/>}/><Route path="/project/:id/advanced" element={<AdvancedSettings/>}/><Route path="/settings" element={<Settings/>}/><Route path="/settings/api" element={<ApiSettings/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes></Layout>}
export default App;
