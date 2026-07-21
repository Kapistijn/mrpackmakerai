import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Check, KeyRound, Loader2, Play, RefreshCw, Save, Server, Trash2, Volume2 } from 'lucide-react';
import { api } from '../lib/api';

type Tab = 'AI' | 'Mod APIs' | 'Voice' | 'System';
const tabs: Tab[] = ['AI', 'Mod APIs', 'Voice', 'System'];

const AI_PROVIDERS = [
  { id: 'lmstudio', label: 'LM Studio', base: 'http://localhost:1234/v1' },
  { id: 'litellm', label: 'LiteLLM', base: 'http://localhost:4000/v1' },
  { id: 'openai', label: 'OpenAI-compatible', base: '' },
];

const TTS_PROVIDERS = [
  { id: 'disabled', label: 'Disabled' },
  { id: 'litellm', label: 'LiteLLM' },
  { id: 'openai', label: 'OpenAI-compatible' },
];

const inputClass = 'w-full rounded-lg bg-surface-overlay border border-surface-border px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-accent';
const labelClass = 'block text-xs uppercase tracking-wide text-gray-500 mb-1';

const Settings = () => {
  const [tab, setTab] = useState<Tab>('AI');
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['settings'], queryFn: () => api.getSettings() });

  // AI form (non-secret fields hydrate from server; api_key is write-only)
  const [provider, setProvider] = useState('lmstudio');
  const [baseUrl, setBaseUrl] = useState('');
  const [model, setModel] = useState('');
  const [temperature, setTemperature] = useState(0.2);
  const [maxTokens, setMaxTokens] = useState(4096);
  const [timeoutSeconds, setTimeoutSeconds] = useState(45);
  const [aiKey, setAiKey] = useState('');

  // Mod catalog keys (write-only)
  const [modrinthKey, setModrinthKey] = useState('');
  const [curseforgeKey, setCurseforgeKey] = useState('');

  // Voice / TTS
  const [whisperUrl, setWhisperUrl] = useState('');
  const [ttsProvider, setTtsProvider] = useState('disabled');
  const [ttsBaseUrl, setTtsBaseUrl] = useState('');
  const [ttsModel, setTtsModel] = useState('');
  const [ttsVoice, setTtsVoice] = useState('alloy');
  const [ttsKey, setTtsKey] = useState('');

  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);
  const [connection, setConnection] = useState<{ reachable: boolean; active_model?: string; detail?: string } | null>(null);
  const [models, setModels] = useState<string[] | null>(null);

  useEffect(() => {
    if (!data) return;
    setProvider(data.ai.provider);
    setBaseUrl(data.ai.base_url);
    setModel(data.ai.model);
    setTemperature(data.ai.temperature);
    setMaxTokens(data.ai.max_tokens);
    setTimeoutSeconds(data.ai.timeout_seconds);
    setWhisperUrl(data.voice.whisper_url);
    setTtsProvider(data.voice.tts_provider);
    setTtsBaseUrl(data.voice.tts_base_url);
    setTtsModel(data.voice.tts_model);
    setTtsVoice(data.voice.tts_voice || 'alloy');
  }, [data]);

  const flash = (kind: 'ok' | 'err', text: string) => {
    setNotice({ kind, text });
    window.setTimeout(() => setNotice(null), 4000);
  };

  const saveAi = async () => {
    setBusy(true);
    try {
      await api.updateSettings({
        ai: {
          provider,
          base_url: baseUrl,
          model,
          temperature,
          max_tokens: maxTokens,
          timeout_seconds: timeoutSeconds,
          ...(aiKey ? { api_key: aiKey } : {}),
        },
      });
      setAiKey('');
      await refetch();
      flash('ok', 'AI settings saved.');
    } catch (err) {
      flash('err', (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const saveKeys = async () => {
    setBusy(true);
    try {
      const update: { modrinth_key?: string; curseforge_key?: string } = {};
      if (modrinthKey) update.modrinth_key = modrinthKey;
      if (curseforgeKey) update.curseforge_key = curseforgeKey;
      await api.updateSettings(update);
      setModrinthKey('');
      setCurseforgeKey('');
      await refetch();
      flash('ok', 'API keys saved (encrypted).');
    } catch (err) {
      flash('err', (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const removeKey = async (name: 'modrinth' | 'curseforge' | 'tts') => {
    setBusy(true);
    try {
      await api.deleteSecret(name);
      await refetch();
      flash('ok', `${name} key deleted.`);
    } catch (err) {
      flash('err', (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const saveVoice = async () => {
    setBusy(true);
    try {
      await api.updateSettings({
        voice: {
          whisper_url: whisperUrl,
          tts_provider: ttsProvider,
          tts_base_url: ttsBaseUrl,
          tts_model: ttsModel,
          tts_voice: ttsVoice,
          ...(ttsKey ? { tts_api_key: ttsKey } : {}),
        },
      });
      setTtsKey('');
      await refetch();
      flash('ok', 'Voice settings saved.');
    } catch (err) {
      flash('err', (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const testConnection = async () => {
    setBusy(true);
    try {
      setConnection(await api.testAiConnection());
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

  const testVoice = async () => {
    setBusy(true);
    try {
      const blob = await api.testTts();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      await audio.play();
      flash('ok', 'Playing TTS sample.');
    } catch (err) {
      flash('err', (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (isLoading) return <div className="flex justify-center py-16"><Loader2 className="w-7 h-7 animate-spin text-accent" /></div>;
  if (error || !data) return <div className="card text-red-400">Settings could not be loaded: {(error as Error).message}</div>;

  const applyProvider = (id: string) => {
    setProvider(id);
    const preset = AI_PROVIDERS.find((p) => p.id === id);
    if (preset && preset.base) setBaseUrl(preset.base);
  };

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-100">Settings</h1>
          <p className="text-gray-400 mt-2">Everything in one place. API keys are sent to the local backend, stored encrypted, and never returned to the browser.</p>
        </div>
        <button className="btn btn-secondary inline-flex gap-2" onClick={() => refetch()}><RefreshCw className="w-4 h-4" />Refresh</button>
      </div>

      {notice && <div className={`rounded-lg p-3 text-sm mb-4 ${notice.kind === 'ok' ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'}`}>{notice.text}</div>}

      <div className="flex gap-2 border-b border-surface-border mb-6 overflow-x-auto">
        {tabs.map((item) => <button key={item} onClick={() => setTab(item)} className={`px-4 py-3 text-sm whitespace-nowrap ${tab === item ? 'text-accent border-b-2 border-accent' : 'text-gray-400'}`}>{item}</button>)}
      </div>

      {tab === 'AI' && <div className="card space-y-5">
        <div className="flex items-center gap-3"><Server className="w-5 h-5 text-accent" /><div><h2 className="font-semibold text-gray-100">AI provider</h2><p className="text-sm text-gray-400">Use LM Studio or LiteLLM — one active at a time.</p></div></div>
        <div>
          <label className={labelClass}>Provider</label>
          <div className="flex gap-2 flex-wrap">
            {AI_PROVIDERS.map((p) => <button key={p.id} type="button" onClick={() => applyProvider(p.id)} className={`px-3 py-2 rounded-lg text-sm border ${provider === p.id ? 'border-accent text-accent bg-accent/10' : 'border-surface-border text-gray-300'}`}>{p.label}</button>)}
          </div>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          <div><label className={labelClass}>Base URL (address)</label><input className={inputClass} value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="http://localhost:1234/v1" /></div>
          <div><label className={labelClass}>Model</label><input className={inputClass} value={model} onChange={(e) => setModel(e.target.value)} placeholder="leave empty for auto-select" list="ai-model-list" />
            {models && <datalist id="ai-model-list">{models.map((m) => <option key={m} value={m} />)}</datalist>}
          </div>
        </div>
        <div className="grid md:grid-cols-3 gap-4">
          <div><label className={labelClass}>Temperature</label><input type="number" step="0.1" min="0" max="2" className={inputClass} value={temperature} onChange={(e) => setTemperature(parseFloat(e.target.value))} /></div>
          <div><label className={labelClass}>Max tokens</label><input type="number" min="128" max="32768" className={inputClass} value={maxTokens} onChange={(e) => setMaxTokens(parseInt(e.target.value, 10))} /></div>
          <div><label className={labelClass}>Timeout (s)</label><input type="number" min="1" max="300" className={inputClass} value={timeoutSeconds} onChange={(e) => setTimeoutSeconds(parseFloat(e.target.value))} /></div>
        </div>
        <div>
          <label className={labelClass}>API key {data.ai.api_key_configured ? '— configured' : '(optional, e.g. LiteLLM)'}</label>
          <div className="flex gap-2">
            <input type="password" className={inputClass} value={aiKey} onChange={(e) => setAiKey(e.target.value)} placeholder={data.ai.api_key_configured ? '•••••• (leave blank to keep)' : 'not set'} />
            {data.ai.api_key_configured && <button type="button" className="btn btn-danger p-2" title="Delete AI key" disabled={busy} onClick={() => api.deleteSecret('ai').then(() => refetch()).then(() => flash('ok', 'AI key deleted.'))}><Trash2 className="w-4 h-4" /></button>}
          </div>
        </div>
        <div className="flex gap-3 flex-wrap">
          <button className="btn btn-primary inline-flex gap-2" disabled={busy} onClick={saveAi}><Save className="w-4 h-4" />Save AI settings</button>
          <button className="btn btn-secondary" disabled={busy} onClick={testConnection}>Test connection</button>
          <button className="btn btn-secondary" disabled={busy} onClick={loadModels}>List models</button>
        </div>
        {connection && <div className={`rounded-lg p-3 text-sm ${connection.reachable ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'}`}>{connection.reachable ? `Connected${connection.active_model ? ` · ${connection.active_model}` : ''}` : connection.detail || 'Not reachable'}</div>}
        {models && <div className="rounded-lg bg-surface-overlay p-4 text-sm"><p className="text-gray-400 mb-2">Available models — click to use</p>{models.length ? <ul className="space-y-1">{models.map((m) => <li key={m}><button type="button" onClick={() => setModel(m)} className={`w-full flex items-center justify-between rounded-md px-3 py-2 text-left ${m === model ? 'bg-accent/20 text-accent' : 'hover:bg-surface-border/60 text-gray-200'}`}><span className="truncate">{m}</span>{m === model && <Check className="w-4 h-4 shrink-0" />}</button></li>)}</ul> : <p>No models were reported.</p>}<p className="text-gray-500 text-xs mt-2">Pick a model, then Save AI settings to persist it.</p></div>}
      </div>}

      {tab === 'Mod APIs' && <div className="card space-y-5">
        <div className="flex items-center gap-3"><KeyRound className="w-5 h-5 text-accent" /><div><h2 className="font-semibold text-gray-100">Mod catalog API keys</h2><p className="text-sm text-gray-400">Modrinth works without a key. CurseForge requires one. Keys are encrypted and can be deleted anytime.</p></div></div>
        <div>
          <label className={labelClass}>Modrinth key ({data.modrinth_key_configured ? `set · ${data.modrinth_key_masked}` : 'optional'})</label>
          <div className="flex gap-2">
            <input type="password" className={inputClass} value={modrinthKey} onChange={(e) => setModrinthKey(e.target.value)} placeholder={data.modrinth_key_configured ? '•••••• (leave blank to keep)' : 'not set'} />
            {data.modrinth_key_configured && <button type="button" className="btn btn-danger p-2" title="Delete Modrinth key" disabled={busy} onClick={() => removeKey('modrinth')}><Trash2 className="w-4 h-4" /></button>}
          </div>
        </div>
        <div>
          <label className={labelClass}>CurseForge key ({data.curseforge_key_configured ? `set · ${data.curseforge_key_masked}` : 'required for CurseForge'})</label>
          <div className="flex gap-2">
            <input type="password" className={inputClass} value={curseforgeKey} onChange={(e) => setCurseforgeKey(e.target.value)} placeholder={data.curseforge_key_configured ? '•••••• (leave blank to keep)' : 'not set'} />
            {data.curseforge_key_configured && <button type="button" className="btn btn-danger p-2" title="Delete CurseForge key" disabled={busy} onClick={() => removeKey('curseforge')}><Trash2 className="w-4 h-4" /></button>}
          </div>
        </div>
        <button className="btn btn-primary inline-flex gap-2" disabled={busy || (!modrinthKey && !curseforgeKey)} onClick={saveKeys}><Save className="w-4 h-4" />Save keys</button>
        <div className="pt-2 border-t border-surface-border"><p className="text-gray-400 text-sm mb-2">Catalog availability</p><div className="space-y-2">{Object.entries(data.mod_sources).map(([source, available]) => <div key={source} className="flex justify-between bg-surface-overlay rounded-lg p-2 text-sm"><span className="capitalize">{source}</span><span className={available ? 'text-green-400' : 'text-gray-500'}>{available ? 'Configured' : 'Not configured'}</span></div>)}</div></div>
      </div>}

      {tab === 'Voice' && <div className="card space-y-5">
        <div className="flex items-center gap-3"><Volume2 className="w-5 h-5 text-accent" /><div><h2 className="font-semibold text-gray-100">Voice (STT & TTS)</h2><p className="text-sm text-gray-400">TTS can run through LiteLLM. Enter the address and model manually.</p></div></div>
        <div><label className={labelClass}>Whisper (STT) URL</label><input className={inputClass} value={whisperUrl} onChange={(e) => setWhisperUrl(e.target.value)} placeholder="http://localhost:9000" /></div>
        <div>
          <label className={labelClass}>TTS provider</label>
          <div className="flex gap-2 flex-wrap">{TTS_PROVIDERS.map((p) => <button key={p.id} type="button" onClick={() => setTtsProvider(p.id)} className={`px-3 py-2 rounded-lg text-sm border ${ttsProvider === p.id ? 'border-accent text-accent bg-accent/10' : 'border-surface-border text-gray-300'}`}>{p.label}</button>)}</div>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          <div><label className={labelClass}>TTS address (base URL)</label><input className={inputClass} value={ttsBaseUrl} onChange={(e) => setTtsBaseUrl(e.target.value)} placeholder="http://localhost:4000/v1" disabled={ttsProvider === 'disabled'} /></div>
          <div><label className={labelClass}>TTS model</label><input className={inputClass} value={ttsModel} onChange={(e) => setTtsModel(e.target.value)} placeholder="e.g. tts-1" disabled={ttsProvider === 'disabled'} /></div>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          <div><label className={labelClass}>Voice</label><input className={inputClass} value={ttsVoice} onChange={(e) => setTtsVoice(e.target.value)} placeholder="alloy" disabled={ttsProvider === 'disabled'} /></div>
          <div><label className={labelClass}>TTS API key {data.voice.tts_api_key_configured ? '— configured' : '(optional)'}</label>
            <div className="flex gap-2">
              <input type="password" className={inputClass} value={ttsKey} onChange={(e) => setTtsKey(e.target.value)} placeholder={data.voice.tts_api_key_configured ? '•••••• (leave blank to keep)' : 'not set'} disabled={ttsProvider === 'disabled'} />
              {data.voice.tts_api_key_configured && <button type="button" className="btn btn-danger p-2" title="Delete TTS key" disabled={busy} onClick={() => removeKey('tts')}><Trash2 className="w-4 h-4" /></button>}
            </div>
          </div>
        </div>
        <div className="flex gap-3 flex-wrap">
          <button className="btn btn-primary inline-flex gap-2" disabled={busy} onClick={saveVoice}><Save className="w-4 h-4" />Save voice settings</button>
          <button className="btn btn-secondary inline-flex gap-2" disabled={busy || !data.voice.tts_enabled} onClick={testVoice}><Play className="w-4 h-4" />Play test</button>
        </div>
        <p className="text-gray-500 text-xs">Save first, then Play test. The backend synthesizes a short sample via POST {'{address}'}/audio/speech.</p>
      </div>}

      {tab === 'System' && <div className="card space-y-3">
        <h2 className="font-semibold text-gray-100">System</h2>
        <p className="text-gray-400 text-sm">Secrets are stored encrypted on disk (Fernet) and never leave the backend. Set <code>MRPACK_SECRET_KEY</code> to control the encryption key; otherwise one is generated in <code>data/.secrets.key</code>.</p>
        <p className="text-gray-400 text-sm">Optional token-gated admin API is {data.admin_locked ? 'enabled' : 'disabled'} (set <code>MRPACK_ADMIN_TOKEN</code> to enable it for shared deployments).</p>
        <p className="text-gray-400 text-sm">Export pipeline: each mod must have a compatible version, download URL, hash, file size and safe filename before an <code>.mrpack</code> is written.</p>
      </div>}
    </div>
  );
};

export default Settings;
