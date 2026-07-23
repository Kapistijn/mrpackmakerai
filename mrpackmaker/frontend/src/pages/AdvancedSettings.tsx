import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';

const themes = ['horror', 'fantasy', 'technology', 'magic', 'adventure', 'rpg', 'survival', 'hardcore', 'exploration', 'vanilla+'];
const gameplay = ['exploration', 'boss fighting', 'building', 'automation', 'farming', 'magic progression', 'combat', 'story driven', 'multiplayer'];

export default function AdvancedSettings() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const projectId = Number(id);
  const { data: project } = useQuery({ queryKey: ['project', projectId], queryFn: () => api.getProject(projectId), enabled: Number.isFinite(projectId) });
  const [theme, setTheme] = useState('');
  const [styles, setStyles] = useState<string[]>([]);
  const [difficulty, setDifficulty] = useState('normal');
  const [minMods, setMinMods] = useState('50');
  const [maxMods, setMaxMods] = useState('');
  const [qol, setQol] = useState('normal');
  const [ram, setRam] = useState('8192');
  const [fps, setFps] = useState('60');
  const [gpu, setGpu] = useState('medium');
  const [shaders, setShaders] = useState('none');
  const [required, setRequired] = useState('');
  const [forbidden, setForbidden] = useState('');

  useEffect(() => {
    if (project) {
      setTheme(project.theme);
      setDifficulty(project.difficulty);
      setMinMods(String(project.minimum_mods ?? 50));
      setMaxMods(project.maximum_mods ? String(project.maximum_mods) : '');
    }
  }, [project]);

  const save = useMutation({
    mutationFn: () => api.updateProject(projectId, {
      generation_prompt: JSON.stringify({ advanced: { theme, gameplay_style: styles, difficulty, minimum_mods: Number(minMods), maximum_mods: maxMods ? Number(maxMods) : null, qol_level: qol, ram_target_mb: Number(ram), fps_target: Number(fps), gpu_class: gpu, shader_support: shaders, required_mods: required.split(',').map(v => v.trim()).filter(Boolean), forbidden_mods: forbidden.split(',').map(v => v.trim()).filter(Boolean) } })
    }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['project', projectId] }); navigate(`/project/${projectId}`); }
  });

  const toggle = (value: string) => setStyles(current => current.includes(value) ? current.filter(item => item !== value) : [...current, value]);
  if (!project) return <div className="card">Loading advanced settings...</div>;
  return <div className="card max-w-4xl">
    <h1 className="text-2xl font-bold text-gray-100 mb-2">Advanced Settings</h1>
    <p className="text-gray-400 mb-6">These settings are saved as structured generation input, not hidden UI state.</p>
    <div className="grid md:grid-cols-2 gap-5">
      <label className="block text-sm text-gray-300">Theme<select className="input mt-2" value={theme} onChange={e => setTheme(e.target.value)}>{themes.map(v => <option key={v}>{v}</option>)}</select></label>
      <label className="block text-sm text-gray-300">Difficulty<select className="input mt-2" value={difficulty} onChange={e => setDifficulty(e.target.value)}>{['easy','normal','hard','extreme','nightmare'].map(v => <option key={v}>{v}</option>)}</select></label>
      <fieldset className="md:col-span-2"><legend className="text-sm text-gray-300 mb-2">Gameplay style</legend><div className="flex flex-wrap gap-2">{gameplay.map(v => <button type="button" key={v} onClick={() => toggle(v)} className={`px-3 py-2 rounded border text-sm ${styles.includes(v) ? 'border-accent bg-accent/20 text-white' : 'border-surface-border text-gray-400'}`}>{v}</button>)}</div></fieldset>
      <label className="block text-sm text-gray-300">Minimum mods<input className="input mt-2" type="number" min="10" value={minMods} onChange={e => setMinMods(e.target.value)} /></label>
      <label className="block text-sm text-gray-300">Maximum mods<input className="input mt-2" type="number" min="1" placeholder="No limit" value={maxMods} onChange={e => setMaxMods(e.target.value)} /></label>
      <label className="block text-sm text-gray-300">QoL level<select className="input mt-2" value={qol} onChange={e => setQol(e.target.value)}>{['none','normal','high','maximum'].map(v => <option key={v}>{v}</option>)}</select></label>
      <label className="block text-sm text-gray-300">GPU class<select className="input mt-2" value={gpu} onChange={e => setGpu(e.target.value)}>{['low','medium','high','extreme'].map(v => <option key={v}>{v}</option>)}</select></label>
      <label className="block text-sm text-gray-300">RAM target (MB)<input className="input mt-2" type="number" min="1024" value={ram} onChange={e => setRam(e.target.value)} /></label>
      <label className="block text-sm text-gray-300">FPS target<select className="input mt-2" value={fps} onChange={e => setFps(e.target.value)}>{['30','60','120','144'].map(v => <option key={v}>{v}</option>)}</select></label>
      <label className="block text-sm text-gray-300">Shader support<select className="input mt-2" value={shaders} onChange={e => setShaders(e.target.value)}>{['none','basic','performance','high_quality'].map(v => <option key={v}>{v}</option>)}</select></label>
      <label className="block text-sm text-gray-300">Loader version<div className="input mt-2 text-gray-500">{project.loader_version || 'Choose on project setup'}</div></label>
      <label className="block text-sm text-gray-300 md:col-span-2">Required mods<input className="input mt-2" placeholder="sodium, jei" value={required} onChange={e => setRequired(e.target.value)} /></label>
      <label className="block text-sm text-gray-300 md:col-span-2">Forbidden mods<input className="input mt-2" placeholder="create, optifine" value={forbidden} onChange={e => setForbidden(e.target.value)} /></label>
    </div>
    <div className="flex justify-end gap-3 mt-8"><button className="btn btn-secondary" onClick={() => navigate(`/project/${projectId}`)}>Cancel</button><button className="btn btn-primary" disabled={save.isPending} onClick={() => save.mutate()}>{save.isPending ? 'Saving...' : 'Save advanced settings'}</button></div>
  </div>;
}
