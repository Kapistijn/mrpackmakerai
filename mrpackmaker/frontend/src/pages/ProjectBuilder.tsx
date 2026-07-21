import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { AIProgressEvent, CompatStatus } from '../types';
import { ArrowLeft, Play, Square, Download, Check, X, AlertTriangle, Loader2, Trash2, ExternalLink } from 'lucide-react';

const ProjectBuilder = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const projectId = parseInt(id || '0');

  const [step, setStep] = useState<1 | 2 | 3 | 4 | 5 | 6>(1);
  const [generationPrompt, setGenerationPrompt] = useState('');
  const [progress, setProgress] = useState<AIProgressEvent | null>(null);
  const [compatibilityReport, setCompatibilityReport] = useState<any>(null);

  const { data: project, isLoading, error } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(projectId),
    enabled: !!projectId,
  });

  const generateMutation = useMutation({
    mutationFn: () => api.startGeneration(projectId),
    onSuccess: () => {
      setStep(3);
      startStreaming();
    },
    onError: (error) => {
      alert(`Failed to start generation: ${(error as Error).message}`);
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => api.cancelGeneration(projectId),
    onSuccess: () => {
      setStep(2);
      setProgress(null);
    },
  });

  const compatibilityMutation = useMutation({
    mutationFn: () => api.checkCompatibility(projectId),
    onSuccess: (report) => {
      setCompatibilityReport(report);
      setStep(5);
    },
    onError: (error) => {
      alert(`Failed to check compatibility: ${(error as Error).message}`);
    },
  });

  const modpackMutation = useMutation({
    mutationFn: () => api.generateModpack(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      setStep(6);
    },
    onError: (error) => {
      alert(`Failed to generate modpack: ${(error as Error).message}`);
    },
  });

  const startStreaming = () => {
    const unsubscribe = api.streamGeneration(
      projectId,
      (event) => {
        setProgress(event);
        if (event.status === 'complete') {
          unsubscribe();
          queryClient.invalidateQueries({ queryKey: ['project', projectId] });
          setStep(4);
        }
      },
      () => {
        unsubscribe();
        queryClient.invalidateQueries({ queryKey: ['project', projectId] });
        setStep(4);
      },
      (error) => {
        unsubscribe();
        alert(`Generation failed: ${error.message}`);
        setStep(2);
      }
    );
  };

  const handleGenerate = () => {
    if (!generationPrompt.trim()) {
      alert('Please enter a generation prompt');
      return;
    }
    api.updateProject(projectId, { generation_prompt: generationPrompt }).then(() => {
      generateMutation.mutate();
    });
  };

  const handleDownload = async () => {
    try {
      const blob = await api.downloadModpack(projectId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = project?.name ? `${project.name.replace(/\s+/g, '-')}.mrpack` : 'modpack.mrpack';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      alert(`Failed to download: ${(error as Error).message}`);
    }
  };

  // Match on source:id, not id alone: a Modrinth and a CurseForge mod can share
  // the same numeric id, and matching by id would remove the wrong mod.
  const handleRemoveMod = async (source: string, modId: string) => {
    if (!project) return;
    const updatedMods = project.mods.filter((m) => !(m.source === source && m.id === modId));
    try {
      await api.updateProject(projectId, { mods: updatedMods });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    } catch (error) {
      alert(`Failed to remove mod: ${(error as Error).message}`);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="card">
        <div className="text-red-400">Failed to load project: {(error as Error)?.message || 'Project not found'}</div>
      </div>
    );
  }

  const steps = [
    { number: 1, title: 'Settings' },
    { number: 2, title: 'AI Prompt' },
    { number: 3, title: 'Generation' },
    { number: 4, title: 'Mods' },
    { number: 5, title: 'Compatibility' },
    { number: 6, title: 'Export' },
  ];

  return (
    <div>
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={() => navigate('/')}
          className="btn btn-secondary p-2"
          title="Back to dashboard"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <h1 className="text-3xl font-bold text-gray-100">{project.name}</h1>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-between mb-8">
        {steps.map((s) => (
          <div key={s.number} className="flex items-center">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${
                step >= s.number
                  ? 'bg-accent text-white'
                  : 'bg-surface-raised border border-surface-border text-gray-400'
              }`}
            >
              {step > s.number ? <Check className="w-5 h-5" /> : s.number}
            </div>
            <span
              className={`ml-2 text-sm ${
                step >= s.number ? 'text-gray-200' : 'text-gray-500'
              }`}
            >
              {s.title}
            </span>
            {s.number < steps.length && (
              <div className="w-16 h-0.5 bg-surface-border mx-4" />
            )}
          </div>
        ))}
      </div>

      {/* Step 1: Settings */}
      {step === 1 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-100 mb-6">Project Settings</h2>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Minecraft Version</label>
              <div className="text-gray-100">{project.minecraft_version}</div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Loader</label>
              <div className="text-gray-100 capitalize">{project.loader}</div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Theme</label>
              <div className="text-gray-100 capitalize">{project.theme}</div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Difficulty</label>
              <div className="text-gray-100 capitalize">{project.difficulty}</div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Priority</label>
              <div className="text-gray-100 capitalize">{project.performance_preference}</div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Description</label>
              <div className="text-gray-100">{project.description}</div>
            </div>
          </div>
          <div className="mt-6 flex justify-end">
            <button onClick={() => setStep(2)} className="btn btn-primary inline-flex items-center gap-2">
              Next
              <ArrowLeft className="w-4 h-4 rotate-180" />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: AI Prompt */}
      {step === 2 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-100 mb-6">AI Generation Prompt</h2>
          <textarea
            className="input min-h-[200px]"
            placeholder="Describe your ideal modpack. For example: 'Make a futuristic technology modpack with lots of automation and high-tech machines.'"
            value={generationPrompt}
            onChange={(e) => setGenerationPrompt(e.target.value)}
          />
          <div className="mt-6 flex justify-between">
            <button onClick={() => setStep(1)} className="btn btn-secondary">
              Back
            </button>
            <button
              onClick={handleGenerate}
              disabled={generateMutation.isPending}
              className="btn btn-primary inline-flex items-center gap-2"
            >
              {generateMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Generate
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Generation Progress */}
      {step === 3 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-100 mb-6">AI Generation Progress</h2>
          {progress && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <Loader2 className="w-6 h-6 animate-spin text-accent" />
                <span className="text-lg text-gray-200">{progress.message}</span>
              </div>
              <div className="w-full bg-surface-border rounded-full h-2">
                <div
                  className="bg-accent h-2 rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(100, Math.max(0, (progress.step / (progress.total_steps || 7)) * 100))}%` }}
                />
              </div>
              <div className="text-sm text-gray-400">
                Step {progress.step} of {progress.total_steps || 7}
              </div>
            </div>
          )}
          <div className="mt-6">
            <button
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending}
              className="btn btn-danger inline-flex items-center gap-2"
            >
              <Square className="w-4 h-4" />
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Mod Overview */}
      {step === 4 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-100 mb-6">Mod Overview ({project.mods.length} mods)</h2>
          {project.ai_summary && (
            <div className="mb-6 p-4 bg-surface-overlay rounded-lg">
              <h3 className="font-medium text-gray-200 mb-2">AI Summary</h3>
              <p className="text-gray-400 text-sm">{project.ai_summary}</p>
            </div>
          )}
          <div className="space-y-3 max-h-[500px] overflow-y-auto">
            {project.mods.map((mod) => (
              <div key={`${mod.source}:${mod.id}`} className="flex items-center gap-4 p-4 bg-surface-overlay rounded-lg">
                {mod.icon_url && (
                  <img src={mod.icon_url} alt={mod.name} className="w-12 h-12 rounded" />
                )}
                <div className="flex-1">
                  <h4 className="font-medium text-gray-200">{mod.name}</h4>
                  <p className="text-sm text-gray-400 line-clamp-1">{mod.summary}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-gray-500 capitalize">{mod.source}</span>
                    <span className="text-xs text-gray-500">•</span>
                    <span className="text-xs text-gray-500">{mod.categories.join(', ')}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-400">{(mod.downloads / 1000000).toFixed(1)}M downloads</div>
                  <a
                    href={mod.project_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-accent hover:underline inline-flex items-center gap-1"
                  >
                    View <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <button
                  onClick={() => handleRemoveMod(mod.source, mod.id)}
                  className="btn btn-danger p-2"
                  title="Remove mod"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
          <div className="mt-6 flex justify-between">
            <button onClick={() => setStep(2)} className="btn btn-secondary">
              Back
            </button>
            <button
              onClick={() => compatibilityMutation.mutate()}
              disabled={compatibilityMutation.isPending}
              className="btn btn-primary inline-flex items-center gap-2"
            >
              {compatibilityMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Checking...
                </>
              ) : (
                'Check Compatibility'
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step 5: Compatibility Report */}
      {step === 5 && compatibilityReport && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-100 mb-6">Compatibility Report</h2>

          <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${
            compatibilityReport.status === CompatStatus.OK ? 'bg-green-900/30' :
            compatibilityReport.status === CompatStatus.WARN ? 'bg-yellow-900/30' :
            'bg-red-900/30'
          }`}>
            {compatibilityReport.status === CompatStatus.OK && <Check className="w-6 h-6 text-green-400" />}
            {compatibilityReport.status === CompatStatus.WARN && <AlertTriangle className="w-6 h-6 text-yellow-400" />}
            {compatibilityReport.status === CompatStatus.ERROR && <X className="w-6 h-6 text-red-400" />}
            <span className="font-medium text-gray-200 capitalize">{compatibilityReport.status}</span>
          </div>

          {compatibilityReport.warnings.length > 0 && (
            <div className="mb-6">
              <h3 className="font-medium text-gray-200 mb-3">Warnings</h3>
              <ul className="space-y-2">
                {compatibilityReport.warnings.map((warning: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-yellow-400 text-sm">
                    <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {compatibilityReport.errors?.length > 0 && (
            <div className="mb-6">
              <h3 className="font-medium text-gray-200 mb-3">Export blockers</h3>
              <ul className="space-y-2">
                {compatibilityReport.errors.map((error: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-red-400 text-sm">
                    <X className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    {error}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mb-6">
            <h3 className="font-medium text-gray-200 mb-3">Mods ({compatibilityReport.mods.length})</h3>
            <div className="space-y-2 max-h-[200px] overflow-y-auto">
              {compatibilityReport.mods.map((item: any, i: number) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  {item.status === CompatStatus.OK && <Check className="w-4 h-4 text-green-400" />}
                  {item.status === CompatStatus.ERROR && <X className="w-4 h-4 text-red-400" />}
                  <span className="text-gray-300">{item.name}</span>
                  <span className="text-gray-500 text-xs ml-auto">{item.message}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="mb-6">
            <h3 className="font-medium text-gray-200 mb-3">Dependencies ({compatibilityReport.dependencies.length})</h3>
            <div className="space-y-2 max-h-[200px] overflow-y-auto">
              {compatibilityReport.dependencies.map((item: any, i: number) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  {item.status === CompatStatus.OK && <Check className="w-4 h-4 text-green-400" />}
                  {item.status === CompatStatus.ERROR && <X className="w-4 h-4 text-red-400" />}
                  <span className="text-gray-300">{item.name}</span>
                  <span className="text-gray-500 text-xs ml-auto">{item.message}</span>
                </div>
              ))}
            </div>
          </div>

          {compatibilityReport.conflicts.length > 0 && (
            <div className="mb-6">
              <h3 className="font-medium text-gray-200 mb-3">Conflicts</h3>
              <div className="space-y-2">
                {compatibilityReport.conflicts.map((item: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-sm text-red-400">
                    <X className="w-4 h-4" />
                    {item.name}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mt-6 flex justify-between">
            <button onClick={() => setStep(4)} className="btn btn-secondary">
              Back
            </button>
            {compatibilityReport.export_ready && (
              <button
                onClick={() => modpackMutation.mutate()}
                disabled={modpackMutation.isPending}
                className="btn btn-primary inline-flex items-center gap-2"
              >
                {modpackMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  'Generate MRPack'
                )}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Step 6: Export */}
      {step === 6 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-100 mb-6">Export Modpack</h2>
          <div className="text-center py-8">
            <Check className="w-16 h-16 text-green-400 mx-auto mb-4" />
            <h3 className="text-2xl font-semibold text-gray-200 mb-2">Modpack Generated Successfully!</h3>
            <p className="text-gray-400 mb-6">
              Your modpack is ready to import into Modrinth App, Prism Launcher, or other MRPack-compatible launchers.
            </p>
            <div className="flex justify-center gap-4">
              <button
                onClick={handleDownload}
                className="btn btn-primary inline-flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download MRPack
              </button>
              <button
                onClick={() => setStep(4)}
                className="btn btn-secondary"
              >
                Back to Mods
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectBuilder;
