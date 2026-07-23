import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { api } from '../lib/api';
import { ProjectSettings, LoaderType, ThemeType, DifficultyType, PerformancePreference } from '../types';
import { ArrowRight, Loader2, RefreshCw } from 'lucide-react';

const MINECRAFT_VERSIONS = ['1.20.1', '1.20.4', '1.21', '1.21.1'];
const LOADERS = [{ value: LoaderType.FABRIC, label: 'Fabric' }, { value: LoaderType.FORGE, label: 'Forge' }, { value: LoaderType.NEOFORGE, label: 'NeoForge' }];
const THEMES = [{ value: ThemeType.TECHNOLOGY, label: 'Technology' }, { value: ThemeType.ADVENTURE, label: 'Adventure' }, { value: ThemeType.MAGIC, label: 'Magic' }, { value: ThemeType.EXPLORATION, label: 'Exploration' }, { value: ThemeType.SURVIVAL, label: 'Survival' }, { value: ThemeType.CUSTOM, label: 'Custom' }];

type LoaderVersion = { id: string; version: string; type: string; published?: string };

const NewProject = () => {
  const navigate = useNavigate();
  const [settings, setSettings] = useState<ProjectSettings>({ minecraft_version: '1.20.1', loader: LoaderType.FABRIC, loader_version: undefined, name: '', description: '', theme: ThemeType.TECHNOLOGY, theme_custom: '', difficulty: DifficultyType.NORMAL, performance_preference: PerformancePreference.BALANCED });
  const [loaderVersions, setLoaderVersions] = useState<LoaderVersion[]>([]);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [versionError, setVersionError] = useState<string | null>(null);

  const loadVersions = async (mc: string, loader: LoaderType) => {
    setLoadingVersions(true); setVersionError(null);
    try {
      const result = await api.getLoaderVersions(mc, loader);
      setLoaderVersions(result.versions);
      setSettings(current => ({ ...current, loader_version: result.versions[0]?.version }));
    } catch (error) {
      setLoaderVersions([]); setSettings(current => ({ ...current, loader_version: undefined }));
      setVersionError((error as Error).message);
    } finally { setLoadingVersions(false); }
  };

  useEffect(() => { void loadVersions(settings.minecraft_version, settings.loader); }, [settings.minecraft_version, settings.loader]);

  const mutation = useMutation({ mutationFn: (data: ProjectSettings) => api.createProject(data), onSuccess: project => navigate(`/project/${project.id}`), onError: error => alert(`Failed to create project: ${(error as Error).message}`) });
  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); if (!settings.name.trim()) return alert('Please enter a project name'); mutation.mutate(settings); };
  const set = <K extends keyof ProjectSettings>(key: K, value: ProjectSettings[K]) => setSettings(current => ({ ...current, [key]: value }));

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-100 mb-2">Create New Project</h1>
      <p className="text-gray-400 mb-8">Choose the exact Minecraft and loader runtime. The selected loader version is stored with the project and used during export.</p>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div><label className="block text-sm font-medium text-gray-300 mb-2">Project Name</label><input type="text" className="input" placeholder="My Awesome Modpack" value={settings.name} onChange={e => set('name', e.target.value)} required /></div>
        <div><label className="block text-sm font-medium text-gray-300 mb-2">Description</label><textarea className="input min-h-[100px]" placeholder="Describe your modpack..." value={settings.description} onChange={e => set('description', e.target.value)} required /></div>
        <div className="grid grid-cols-2 gap-4">
          <div><label className="block text-sm font-medium text-gray-300 mb-2">Minecraft Version</label><select className="input" value={settings.minecraft_version} onChange={e => set('minecraft_version', e.target.value)}>{MINECRAFT_VERSIONS.map(v => <option key={v}>{v}</option>)}</select></div>
          <div><label className="block text-sm font-medium text-gray-300 mb-2">Loader</label><select className="input" value={settings.loader} onChange={e => set('loader', e.target.value as LoaderType)}>{LOADERS.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}</select></div>
        </div>
        <div className="rounded-lg border border-surface-border bg-surface-overlay p-4">
          <div className="flex items-center justify-between mb-2"><label className="block text-sm font-medium text-gray-300">Loader Version</label><button type="button" className="text-xs text-accent inline-flex items-center gap-1" onClick={() => void loadVersions(settings.minecraft_version, settings.loader)}><RefreshCw className="w-3 h-3" /> Refresh</button></div>
          {loadingVersions ? <div className="text-sm text-gray-400 inline-flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Loading compatible versions...</div> : versionError ? <div className="text-sm text-red-400">{versionError}</div> : <><select className="input" value={settings.loader_version || ''} onChange={e => set('loader_version', e.target.value || undefined)}><option value="">Auto-select latest stable</option>{loaderVersions.filter(v => v.type === 'release').map(v => <option key={v.id} value={v.version}>{v.version} (stable)</option>)}{loaderVersions.filter(v => v.type !== 'release').map(v => <option key={v.id} value={v.version}>{v.version} ({v.type})</option>)}</select><p className="text-xs text-gray-500 mt-2">Stable releases are listed first. Auto-select is safe when you do not need to pin a runtime.</p></>}
        </div>
        <div><label className="block text-sm font-medium text-gray-300 mb-2">Theme</label><select className="input" value={settings.theme} onChange={e => set('theme', e.target.value as ThemeType)}>{THEMES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}</select></div>
        {settings.theme === ThemeType.CUSTOM && <div><label className="block text-sm font-medium text-gray-300 mb-2">Custom Theme</label><input type="text" className="input" placeholder="e.g., Medieval, Space, Horror" value={settings.theme_custom} onChange={e => set('theme_custom', e.target.value)} /></div>}
        <div className="grid grid-cols-2 gap-4"><div><label className="block text-sm font-medium text-gray-300 mb-2">Difficulty</label><select className="input" value={settings.difficulty} onChange={e => set('difficulty', e.target.value as DifficultyType)}><option value={DifficultyType.CASUAL}>Casual</option><option value={DifficultyType.NORMAL}>Normal</option><option value={DifficultyType.HARD}>Hard</option><option value={DifficultyType.EXPERT}>Expert</option></select></div><div><label className="block text-sm font-medium text-gray-300 mb-2">Priority</label><select className="input" value={settings.performance_preference} onChange={e => set('performance_preference', e.target.value as PerformancePreference)}><option value={PerformancePreference.BALANCED}>Balanced</option><option value={PerformancePreference.PERFORMANCE}>Performance</option><option value={PerformancePreference.VISUALS}>Visual quality</option></select></div></div>
        <div className="flex justify-end"><button type="submit" disabled={mutation.isPending || loadingVersions} className="btn btn-primary inline-flex items-center gap-2">{mutation.isPending ? <><Loader2 className="w-4 h-4 animate-spin" /> Creating...</> : <>Create Project <ArrowRight className="w-4 h-4" /></>}</button></div>
      </form>
    </div>
  );
};
export default NewProject;
