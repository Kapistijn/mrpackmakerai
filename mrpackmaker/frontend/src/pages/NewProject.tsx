import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { api } from '../lib/api';
import { ProjectSettings, LoaderType, ThemeType, DifficultyType, PerformancePreference } from '../types';
import { ArrowRight, Loader2 } from 'lucide-react';

const MINECRAFT_VERSIONS = ['1.20.1', '1.20.4', '1.21', '1.21.1'];
const LOADERS = [
  { value: LoaderType.FABRIC, label: 'Fabric' },
  { value: LoaderType.FORGE, label: 'Forge' },
  { value: LoaderType.NEOFORGE, label: 'NeoForge' },
];
const THEMES = [
  { value: ThemeType.TECHNOLOGY, label: 'Technology' },
  { value: ThemeType.ADVENTURE, label: 'Adventure' },
  { value: ThemeType.MAGIC, label: 'Magic' },
  { value: ThemeType.EXPLORATION, label: 'Exploration' },
  { value: ThemeType.SURVIVAL, label: 'Survival' },
  { value: ThemeType.CUSTOM, label: 'Custom' },
];

const NewProject = () => {
  const navigate = useNavigate();
  const [settings, setSettings] = useState<ProjectSettings>({
    minecraft_version: '1.20.1',
    loader: LoaderType.FABRIC,
    name: '',
    description: '',
    theme: ThemeType.TECHNOLOGY,
    theme_custom: '',
    difficulty: DifficultyType.NORMAL,
    performance_preference: PerformancePreference.BALANCED,
  });

  const mutation = useMutation({
    mutationFn: (data: ProjectSettings) => api.createProject(data),
    onSuccess: (project) => {
      navigate(`/project/${project.id}`);
    },
    onError: (error) => {
      alert(`Failed to create project: ${(error as Error).message}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings.name.trim()) {
      alert('Please enter a project name');
      return;
    }
    mutation.mutate(settings);
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-100 mb-8">Create New Project</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Project Name</label>
          <input
            type="text"
            className="input"
            placeholder="My Awesome Modpack"
            value={settings.name}
            onChange={(e) => setSettings({ ...settings, name: e.target.value })}
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Description</label>
          <textarea
            className="input min-h-[100px]"
            placeholder="Describe your modpack..."
            value={settings.description}
            onChange={(e) => setSettings({ ...settings, description: e.target.value })}
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Minecraft Version</label>
            <select
              className="input"
              value={settings.minecraft_version}
              onChange={(e) => setSettings({ ...settings, minecraft_version: e.target.value })}
            >
              {MINECRAFT_VERSIONS.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Loader</label>
            <select
              className="input"
              value={settings.loader}
              onChange={(e) => setSettings({ ...settings, loader: e.target.value as LoaderType })}
            >
              {LOADERS.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Theme</label>
          <select
            className="input"
            value={settings.theme}
            onChange={(e) => setSettings({ ...settings, theme: e.target.value as ThemeType })}
          >
            {THEMES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        {settings.theme === ThemeType.CUSTOM && (
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Custom Theme</label>
            <input
              type="text"
              className="input"
              placeholder="e.g., Medieval, Space, Horror"
              value={settings.theme_custom}
              onChange={(e) => setSettings({ ...settings, theme_custom: e.target.value })}
            />
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Difficulty</label>
            <select
              className="input"
              value={settings.difficulty}
              onChange={(e) => setSettings({ ...settings, difficulty: e.target.value as DifficultyType })}
            >
              <option value={DifficultyType.CASUAL}>Casual</option>
              <option value={DifficultyType.NORMAL}>Normal</option>
              <option value={DifficultyType.HARD}>Hard</option>
              <option value={DifficultyType.EXPERT}>Expert</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Priority</label>
            <select
              className="input"
              value={settings.performance_preference}
              onChange={(e) => setSettings({ ...settings, performance_preference: e.target.value as PerformancePreference })}
            >
              <option value={PerformancePreference.BALANCED}>Balanced</option>
              <option value={PerformancePreference.PERFORMANCE}>Performance</option>
              <option value={PerformancePreference.VISUALS}>Visual quality</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="btn btn-primary inline-flex items-center gap-2"
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                Create Project
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default NewProject;
