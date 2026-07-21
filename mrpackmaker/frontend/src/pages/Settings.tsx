import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Check, CircleOff, Loader2, RefreshCw, Server, Volume2 } from 'lucide-react';
import { api } from '../lib/api';
import { ApiTestResult } from '../types';

type Tab = 'AI' | 'Voice' | 'APIs' | 'System' | 'Admin';

const tabs: Tab[] = ['AI', 'Voice', 'APIs', 'System', 'Admin'];

const Settings = () => {
  const [tab, setTab] = useState<Tab>('AI');
  const [connection, setConnection] = useState<ApiTestResult | null>(null);
  const [models, setModels] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [selecting, setSelecting] = useState<string | null>(null);
  const [selectError, setSelectError] = useState<string | null>(null);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.getSettings(),
  });

  const testConnection = async () => {
    setBusy(true);
    try {
      setConnection(await api.testAiConnection());
    } finally {
      setBusy(false);
    }
  };

  const loadModels = async () => {
    setBusy(true);
    try {
      const result = await api.getAiModels();
      setModels(result.models);
    } finally {
      setBusy(false);
    }
  };

  const selectModel = async (model: string) => {
    setSelecting(model);
    setSelectError(null);
    try {
      await api.setAiModel(model);
      await refetch();
    } catch (err) {
      setSelectError((err as Error).message);
    } finally {
      setSelecting(null);
    }
  };

  if (isLoading) return <div className="flex justify-center py-16"><Loader2 className="w-7 h-7 animate-spin text-accent" /></div>;
  if (error || !data) return <div className="card text-red-400">Settings could not be loaded: {(error as Error).message}</div>;

  const activeModel = data.ai.model;

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-100">Settings</h1>
          <p className="text-gray-400 mt-2">Connections are handled by the backend; secrets never enter the browser. For API keys, use the API page.</p>
        </div>
        <button className="btn btn-secondary inline-flex gap-2" onClick={() => refetch()}><RefreshCw className="w-4 h-4" />Refresh</button>
      </div>
      <div className="flex gap-2 border-b border-surface-border mb-6 overflow-x-auto">
        {tabs.map((item) => <button key={item} onClick={() => setTab(item)} className={`px-4 py-3 text-sm ${tab === item ? 'text-accent border-b-2 border-accent' : 'text-gray-400'}`}>{item}</button>)}
      </div>

      {tab === 'AI' && <div className="card space-y-5">
        <div className="flex items-center gap-3"><Server className="w-5 h-5 text-accent" /><div><h2 className="font-semibold text-gray-100">{data.ai.provider}</h2><p className="text-sm text-gray-400">{data.ai.base_url}</p></div></div>
        <div className="grid grid-cols-2 gap-4 text-sm"><div><span className="text-gray-500">Active model</span><p>{activeModel || 'Auto-select first available model'}</p></div><div><span className="text-gray-500">Generation policy</span><p>{data.ai.max_tokens} tokens · temperature {data.ai.temperature} · ctx {data.ai.context_size}</p></div></div>
        <div className="flex gap-3"><button className="btn btn-primary" disabled={busy} onClick={testConnection}>Test connection</button><button className="btn btn-secondary" disabled={busy} onClick={loadModels}>List models</button></div>
        {connection && <div className={`rounded-lg p-3 text-sm ${connection.ok ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'}`}>{connection.ok ? `Connected${connection.info?.model ? ` · ${connection.info.model}` : ''}${connection.latency_ms != null ? ` · ${connection.latency_ms}ms` : ''}` : connection.detail || 'Not reachable'}</div>}
        {selectError && <div className="rounded-lg p-3 text-sm bg-red-900/30 text-red-300">{selectError}</div>}
        {models && <div className="rounded-lg bg-surface-overlay p-4 text-sm">
          <p className="text-gray-400 mb-2">Available models — click one to activate</p>
          {models.length ? <ul className="space-y-1">{models.map(model => {
            const isActive = model === activeModel;
            return (
              <li key={model}>
                <button
                  type="button"
                  disabled={selecting !== null}
                  onClick={() => selectModel(model)}
                  className={`w-full flex items-center justify-between rounded-md px-3 py-2 text-left transition-colors ${isActive ? 'bg-accent/20 text-accent' : 'hover:bg-surface-border/60 text-gray-200'}`}
                >
                  <span className="truncate">{model}</span>
                  {selecting === model ? <Loader2 className="w-4 h-4 animate-spin shrink-0" /> : isActive ? <Check className="w-4 h-4 shrink-0" /> : null}
                </button>
              </li>
            );
          })}</ul> : <p>No models were reported.</p>}
          {activeModel && <button type="button" disabled={selecting !== null} onClick={() => selectModel('')} className="mt-3 text-xs text-gray-400 hover:text-gray-200 underline">Reset to auto-select</button>}
        </div>}
      </div>}

      {tab === 'Voice' && <div className="card"><div className="flex gap-3"><Volume2 className="w-5 h-5 text-accent" /><div><h2 className="font-semibold">Voice service boundary</h2><p className="text-gray-400 text-sm mt-1">Whisper endpoint: {data.voice.whisper_url}</p><p className="text-gray-400 text-sm">TTS provider: {data.voice.tts_provider}</p><p className="text-gray-500 text-sm mt-4">Voice providers run independently and can be replaced without changing generation jobs.</p></div></div></div>}

      {tab === 'APIs' && <div className="card"><h2 className="font-semibold mb-4">Mod catalog sources</h2><div className="space-y-3">{Object.entries(data.mod_sources).map(([source, available]) => <div key={source} className="flex justify-between bg-surface-overlay rounded-lg p-3"><span className="capitalize">{source}</span><span className={available ? 'text-green-400' : 'text-gray-500'}>{available ? 'Configured' : 'Not configured'}</span></div>)}</div><p className="text-gray-500 text-sm mt-4">Manage API keys and run connection tests on the API page.</p></div>}

      {tab === 'System' && <div className="card"><h2 className="font-semibold mb-3">Safe export pipeline</h2><p className="text-gray-400 text-sm">Each mod must have a compatible version, download URL, hash, file size and safe filename. Exports are validated before their archive replaces a previous pack.</p></div>}

      {tab === 'Admin' && <div className="card"><div className="flex gap-3"><CircleOff className="w-5 h-5 text-yellow-400" /><div><h2 className="font-semibold">Admin settings are protected</h2><p className="text-gray-400 text-sm mt-1">Set <code>MRPACK_ADMIN_TOKEN</code> (at least 16 characters) to enable protected configuration. API keys are masked in responses and stored encrypted on disk when updated through the admin API.</p></div></div></div>}
    </div>
  );
};

export default Settings;
