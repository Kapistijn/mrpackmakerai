import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Check, KeyRound, Loader2, RefreshCw, Save, Server, Trash2, Zap } from 'lucide-react';
import { api } from '../lib/api';
import { ApiTestResult } from '../types';
import HelpTip from '../components/HelpTip';

const AI_PROVIDERS = [
  { id: 'lmstudio', label: 'LM Studio', base: 'http://localhost:1234/v1' },
  { id: 'litellm', label: 'LiteLLM', base: 'http://localhost:4000/v1' },
  { id: 'openai', label: 'OpenAI-compatible', base: '' },
];

const CONTEXT_SIZES = [1024, 2048, 4096, 8192, 16384, 32768];

const CONTEXT_HELP = `Context size bepaalt hoeveel informatie de AI tegelijk kan onthouden.

1024: weinig geheugen, sneller, vergeet eerdere info sneller
2048: normaal gebruik
4096: aangeraden — goede balans voor de meeste modpacks
8192: voor grote modpacks, meer RAM/VRAM nodig
16384+: alleen krachtige systemen`;

const MAX_TOKENS_HELP = `Max tokens bepaalt hoe lang de AI-antwoorden mogen zijn.

1024: korte antwoorden
4096: aangeraden
8192: lange antwoorden`;

const TEMPERATURE_HELP = `Temperature bepaalt creativiteit.

0.0: zeer precies, beste voor JSON
0.2: aanbevolen
0.7: creatiever
1.0: veel variatie`;

const inputClass = 'w-full rounded-lg bg-surface-overlay border border-surface-border px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-accent';
const labelClass = 'flex items-center gap-1 text-xs uppercase tracking-wide text-gray-500 mb-1';

const StatusBadge = ({ configured }: { configured: boolean }) => (
  <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs ${configured ? 'bg-green-900/30 text-green-300' : 'bg-surface-overlay text-gray-400'}`}>
    {configured ? <><Check className="w-3 h-3" /> Configured</> : 'Not configured'}
  </span>
);

const TestResultBox = ({ result }: { result: ApiTestResult }) => (
  <div className={`rounded-lg p-3 text-sm ${result.ok ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'}`}>
    <div className="font-medium">{result.ok ? `✓ ${result.detail || 'Works'}` : `✗ ${result.detail || 'Failed'}`}</div>
    <div className="mt-1 text-xs opacity-90 space-y-0.5">
      {result.status_code != null && <div>Response: {result.status_code}</div>}
      {result.latency_ms != null && <div>Latency: {result.latency_ms}ms</div>}
      {Object.entries(result.info || {}).map(([k, v]) => v && <div key={k}>{k}: {v}</div>)}
    </div>
  </div>
);

const ApiSettings = () => {
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['settings'], queryFn: () => api.getSettings() });

  const [provider, setProvider] = useState('lmstudio');
  const [baseUrl, setBaseUrl] = useState('');
  const [model, setModel] = useState('');
  const [contextSize, setContextSize] = useState(4096);
  const [maxTokens, setMaxTokens] = useState(4096);
  const [temperature, setTemperature] = useState(0.2);
  const [aiKey, setAiKey] = useState('');
  const [modrinthKey, setModrinthKey] = useState('');
  const [curseforgeKey, setCurseforgeKey] = useState('');

  const [models, setModels] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);
  const [aiResult, setAiResult] = useState<ApiTestResult | null>(null);
  const [modrinthResult, setModrinthResult] = useState<ApiTestResult | null>(null);
  const [curseforgeResult, setCurseforgeResult] = useState<ApiTestResult | null>(null);

  useEffect(() => {
    if (!data) return;
    setProvider(data.ai.provider);
    setBaseUrl(data.ai.base_url);
    setModel(data.ai.model);
    setContextSize(data.ai.context_size);
    setMaxTokens(data.ai.max_tokens);
    setTemperature(data.ai.temperature);
  }, [data]);

  const flash = (kind: 'ok' | 'err', text: string) => {
    setNotice({ kind, text });
    window.setTimeout(() => setNotice(null), 4000);
  };

  const applyProvider = (id: string) => {
    setProvider(id);
    const preset = AI_PROVIDERS.find((p) => p.id === id);
    if (preset && preset.base) setBaseUrl(preset.base);
  };

  const saveAi = async () => {
    setBusy(true);
    try {
      await api.updateSettings({
        ai: {
          provider,
          base_url: baseUrl,
          model,
          context_size: contextSize,
          max_tokens: maxTokens,
          temperature,
          ...(aiKey ? { api_key: aiKey } : {}),
        },
      });
      setAiKey('');
      await refetch();
      flash('ok', 'AI configuration saved.');
    } catch (err) {
      flash('err', (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const saveKey = async (which: 'modrinth' | 'curseforge') => {
    setBusy(true);
    try {
      await api.updateSettings(which === 'modrinth' ? { modrinth_key: modrinthKey } : { curseforge_key: curseforgeKey });
      if (which === 'modrinth') setModrinthKey(''); else setCurseforgeKey('');
      await refetch();
      flash('ok', `${which} key saved (encrypted).`);
    } catch (err) {
      flash('err', (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const removeKey = async (which: 'ai' | 'modrinth' | 'curseforge') => {
    setBusy(true);
    try {
      await api.deleteSecret(which);
      await refetch();
      flash('ok', `${which} key deleted.`);
    } catch (err) {
      flash('err', (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const loadModels = async () => {
    setBusy(true);
    try {
      const result = await api.getAiModels();
      setModels(result.models);
      if (!model && result.models.length) setModel(result.models[0]);
    } catch (err) {
      flash('err', (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const runTest = async (
    which: 'ai' | 'modrinth' | 'curseforge',
    fn: () => Promise<ApiTestResult>,
    setter: (r: ApiTestResult) => void,
  ) => {
    setBusy(true);
    try {
      setter(await fn());
    } catch (err) {
      setter({ ok: false, service: which, detail: (err as Error).message, info: {} });
    } finally {
      setBusy(false);
    }
  };

  if (isLoading) return <div className="flex justify-center py-16"><Loader2 className="w-7 h-7 animate-spin text-accent" /></div>;
  if (error || !data) return <div className="card text-red-400">Settings could not be loaded: {(error as Error).message}</div>;

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-100">API Settings</h1>
          <p className="text-gray-400 mt-2">All keys are entered here, encrypted on disk, and never returned to the browser.</p>
        </div>
        <button className="btn btn-secondary inline-flex gap-2" onClick={() => refetch()}><RefreshCw className="w-4 h-4" />Refresh</button>
      </div>

      {notice && <div className={`rounded-lg p-3 text-sm mb-6 ${notice.kind === 'ok' ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'}`}>{notice.text}</div>}

      {/* AI Configuration */}
      <div className="card space-y-5 mb-6">
        <div className="flex items-center gap-3"><Server className="w-5 h-5 text-accent" /><h2 className="font-semibold text-gray-100">AI Configuration</h2></div>

        <div>
          <label className={labelClass}>Provider</label>
          <div className="flex gap-2 flex-wrap">
            {AI_PROVIDERS.map((p) => <button key={p.id} type="button" onClick={() => applyProvider(p.id)} className={`px-3 py-2 rounded-lg text-sm border ${provider === p.id ? 'border-accent text-accent bg-accent/10' : 'border-surface-border text-gray-300'}`}>{p.label}</button>)}
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div><label className={labelClass}>API URL</label><input className={inputClass} value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="http://localhost:1234/v1" /></div>
          <div>
            <label className={labelClass}>Model</label>
            <input className={inputClass} value={model} onChange={(e) => setModel(e.target.value)} placeholder="leave empty for auto-select" list="api-model-list" />
            {models && <datalist id="api-model-list">{models.map((m) => <option key={m} value={m} />)}</datalist>}
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-4">
          <div>
            <label className={labelClass}>Context Size <HelpTip title="Context Size" text={CONTEXT_HELP} /></label>
            <select className={inputClass} value={contextSize} onChange={(e) => setContextSize(parseInt(e.target.value, 10))}>
              {CONTEXT_SIZES.map((c) => <option key={c} value={c}>{c}{c === 4096 ? ' (recommended)' : ''}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>Max Tokens <HelpTip title="Max Tokens" text={MAX_TOKENS_HELP} /></label>
            <input type="number" min={128} max={32768} className={inputClass} value={maxTokens} onChange={(e) => setMaxTokens(parseInt(e.target.value, 10))} />
          </div>
          <div>
            <label className={labelClass}>Temperature <HelpTip title="Temperature" text={TEMPERATURE_HELP} /></label>
            <input type="number" step={0.1} min={0} max={2} className={inputClass} value={temperature} onChange={(e) => setTemperature(parseFloat(e.target.value))} />
          </div>
        </div>

        <div>
          <label className={labelClass}>AI API Key {data.ai.api_key_configured && <span className="text-green-400 normal-case">— configured</span>}</label>
          <div className="flex gap-2">
            <input type="password" className={inputClass} value={aiKey} onChange={(e) => setAiKey(e.target.value)} placeholder={data.ai.api_key_configured ? '•••••••••••••••• (leave blank to keep)' : 'optional — e.g. LiteLLM key'} />
            {data.ai.api_key_configured && <button type="button" className="btn btn-danger p-2" title="Delete AI key" disabled={busy} onClick={() => removeKey('ai')}><Trash2 className="w-4 h-4" /></button>}
          </div>
        </div>

        <div className="flex gap-3 flex-wrap">
          <button className="btn btn-primary inline-flex gap-2" disabled={busy} onClick={saveAi}><Save className="w-4 h-4" />Save</button>
          <button className="btn btn-secondary" disabled={busy} onClick={loadModels}>List models</button>
          <button className="btn btn-secondary inline-flex gap-2" disabled={busy} onClick={() => runTest('ai', () => api.testAiConnection(), setAiResult)}><Zap className="w-4 h-4" />Test AI Connection</button>
        </div>
        {aiResult && <TestResultBox result={aiResult} />}
      </div>

      {/* Modrinth */}
      <div className="card space-y-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3"><KeyRound className="w-5 h-5 text-accent" /><h2 className="font-semibold text-gray-100">Modrinth API</h2></div>
          <StatusBadge configured={data.modrinth_key_configured} />
        </div>
        <p className="text-sm text-gray-400">Modrinth works without a key; add one only to raise rate limits. Stored: {data.modrinth_key_masked}</p>
        <div className="flex gap-2">
          <input type="password" className={inputClass} value={modrinthKey} onChange={(e) => setModrinthKey(e.target.value)} placeholder={data.modrinth_key_configured ? '•••••• (leave blank to keep)' : 'enter Modrinth API key'} />
          {data.modrinth_key_configured && <button type="button" className="btn btn-danger p-2" title="Delete Modrinth key" disabled={busy} onClick={() => removeKey('modrinth')}><Trash2 className="w-4 h-4" /></button>}
        </div>
        <div className="flex gap-3 flex-wrap">
          <button className="btn btn-primary inline-flex gap-2" disabled={busy || !modrinthKey} onClick={() => saveKey('modrinth')}><Save className="w-4 h-4" />Save</button>
          <button className="btn btn-secondary inline-flex gap-2" disabled={busy} onClick={() => runTest('modrinth', () => api.testModrinth(), setModrinthResult)}><Zap className="w-4 h-4" />Test Modrinth API</button>
        </div>
        {modrinthResult && <TestResultBox result={modrinthResult} />}
      </div>

      {/* CurseForge */}
      <div className="card space-y-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3"><KeyRound className="w-5 h-5 text-accent" /><h2 className="font-semibold text-gray-100">CurseForge API</h2></div>
          <StatusBadge configured={data.curseforge_key_configured} />
        </div>
        <p className="text-sm text-gray-400">A CurseForge key is required to use CurseForge as a source. Stored: {data.curseforge_key_masked}</p>
        <div className="flex gap-2">
          <input type="password" className={inputClass} value={curseforgeKey} onChange={(e) => setCurseforgeKey(e.target.value)} placeholder={data.curseforge_key_configured ? '•••••• (leave blank to keep)' : 'enter CurseForge API key'} />
          {data.curseforge_key_configured && <button type="button" className="btn btn-danger p-2" title="Delete CurseForge key" disabled={busy} onClick={() => removeKey('curseforge')}><Trash2 className="w-4 h-4" /></button>}
        </div>
        <div className="flex gap-3 flex-wrap">
          <button className="btn btn-primary inline-flex gap-2" disabled={busy || !curseforgeKey} onClick={() => saveKey('curseforge')}><Save className="w-4 h-4" />Save</button>
          <button className="btn btn-secondary inline-flex gap-2" disabled={busy} onClick={() => runTest('curseforge', () => api.testCurseforge(), setCurseforgeResult)}><Zap className="w-4 h-4" />Test CurseForge API</button>
        </div>
        {curseforgeResult && <TestResultBox result={curseforgeResult} />}
      </div>
    </div>
  );
};

export default ApiSettings;
