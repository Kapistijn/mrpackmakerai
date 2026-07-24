import { Link, useLocation } from 'react-router-dom';
import { Blocks, Home, KeyRound, Plus, Settings, SlidersHorizontal, Sparkles } from 'lucide-react';

const Layout = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();
  const projectMatch = location.pathname.match(/^\/project\/(\d+)/);
  const projectId = projectMatch?.[1];
  const isActive = (path: string) => location.pathname === path;
  return <div className="min-h-screen bg-surface">
    <nav className="bg-surface-raised border-b border-surface-border"><div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"><div className="flex items-center justify-between h-16"><div className="flex items-center gap-8">
      <Link to="/" className="flex items-center gap-2 text-xl font-bold text-accent"><Blocks className="w-8 h-8" /><span>MrPackMaker</span></Link>
      <div className="flex gap-4">
        <Link to="/" className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${isActive('/') ? 'bg-surface-overlay text-accent' : 'text-gray-400 hover:text-gray-200'}`}><Home className="w-4 h-4" /><span>Dashboard</span></Link>
        <Link to="/new" className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${isActive('/new') ? 'bg-surface-overlay text-accent' : 'text-gray-400 hover:text-gray-200'}`}><Plus className="w-4 h-4" /><span>New Project</span></Link>
        {projectId && <Link to={`/project/${projectId}/advanced`} className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${location.pathname.endsWith('/advanced') ? 'bg-surface-overlay text-accent' : 'text-gray-400 hover:text-gray-200'}`}><SlidersHorizontal className="w-4 h-4" /><span>Advanced</span></Link>}
        {projectId && <Link to={`/project/${projectId}/insights`} className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${location.pathname.endsWith('/insights') ? 'bg-surface-overlay text-accent' : 'text-gray-400 hover:text-gray-200'}`}><Sparkles className="w-4 h-4" /><span>Insights</span></Link>}
        <Link to="/settings" className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${isActive('/settings') ? 'bg-surface-overlay text-accent' : 'text-gray-400 hover:text-gray-200'}`}><Settings className="w-4 h-4" /><span>Settings</span></Link>
        <Link to="/settings/api" className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${isActive('/settings/api') ? 'bg-surface-overlay text-accent' : 'text-gray-400 hover:text-gray-200'}`}><KeyRound className="w-4 h-4" /><span>API</span></Link>
      </div>
    </div></div></div></nav>
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">{children}</main>
  </div>;
};
export default Layout;
