import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { ProjectStatus } from '../types';
import { formatDistance } from 'date-fns';
import { ArrowRight, Trash2 } from 'lucide-react';

const statusColors: Record<ProjectStatus, string> = {
  [ProjectStatus.DRAFT]: 'status-draft',
  [ProjectStatus.GENERATING]: 'status-generating',
  [ProjectStatus.REVIEW]: 'status-review',
  [ProjectStatus.READY]: 'status-ready',
  [ProjectStatus.EXPORTED]: 'status-exported',
};

const Dashboard = () => {
  const { data: projects, isLoading, error } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.getProjects(),
  });

  const handleDelete = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this project?')) {
      try {
        await api.deleteProject(id);
        window.location.reload();
      } catch (err) {
        alert('Failed to delete project');
      }
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading projects...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="text-red-400">Failed to load projects: {(error as Error).message}</div>
      </div>
    );
  }

  if (!projects || projects.length === 0) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold text-gray-200 mb-4">No projects yet</h2>
        <p className="text-gray-400 mb-8">Create your first AI-generated Minecraft modpack</p>
        <Link to="/new" className="btn btn-primary inline-flex items-center gap-2">
          Create Project
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-gray-100">Dashboard</h1>
        <Link to="/new" className="btn btn-primary inline-flex items-center gap-2">
          New Project
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      <div className="grid gap-4">
        {projects.map((project) => (
          <div key={project.id} className="card hover:border-accent transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-xl font-semibold text-gray-100">{project.name}</h3>
                  <span className={`status-badge ${statusColors[project.status]}`}>
                    {project.status}
                  </span>
                </div>
                <div className="text-sm text-gray-400 space-y-1">
                  <div>Minecraft {project.minecraft_version} • {project.loader}</div>
                  <div>Last updated {formatDistance(new Date(project.updated_at), new Date(), { addSuffix: true })}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Link
                  to={`/project/${project.id}`}
                  className="btn btn-secondary inline-flex items-center gap-2"
                >
                  Open
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <button
                  onClick={() => handleDelete(project.id)}
                  className="btn btn-danger p-2"
                  title="Delete project"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Dashboard;
