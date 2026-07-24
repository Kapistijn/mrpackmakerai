import {useState} from 'react';
import {useParams,useNavigate} from 'react-router-dom';
import {useQuery,useMutation} from '@tanstack/react-query';
import {api} from '../lib/api';
import {Loader2,Sparkles,Gauge,Users,ShieldCheck,GitCompare} from 'lucide-react';
const Bar=({label,value,bar}:{label:string;value:number;bar:string})=>(
  <div className="mb-2"><div className="flex justify-between text-sm text-gray-300"><span className="capitalize">{label.replace('_',' ')}</span><span>{value}</span></div><div className="font-mono text-accent text-sm">{bar}</div></div>
);
export default function PackInsights(){
  const {id}=useParams();
  const navigate=useNavigate();
  const projectId=Number(id);
  const insights=useQuery({queryKey:['insights',projectId],queryFn:()=>api.getPackInsights(projectId),enabled:Number.isFinite(projectId)});
  const [prompt,setPrompt]=useState('');
  const [plan,setPlan]=useState<any>();
  const [update,setUpdate]=useState<any>();
  const nl=useMutation({mutationFn:()=>api.proposeNaturalLanguageEdit(projectId,prompt),onSuccess:setPlan});
  const safeUpdate=useMutation({mutationFn:()=>api.planSafeUpdate(projectId),onSuccess:setUpdate});
  if(insights.isLoading)return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-accent"/></div>;
  if(insights.error)return <div className="card text-red-400">Failed to load insights: {(insights.error as Error).message}</div>;
  const d:any=insights.data||{};
  return <div className="max-w-4xl mx-auto space-y-6">
    <div className="flex justify-between items-center">
      <h1 className="text-3xl font-bold text-gray-100 inline-flex items-center gap-2"><Sparkles className="w-7 h-7 text-accent"/>Pack Intelligence</h1>
      <button className="btn btn-secondary" onClick={()=>navigate(`/project/${projectId}`)}>Back to Builder</button>
    </div>
    <section className="card">
      <h2 className="text-xl font-semibold mb-4">Quality Score</h2>
      {d.quality&&<><div>{Object.entries(d.quality.scores||{}).map(([k,v]:any)=><Bar key={k} label={k} value={v as number} bar={(d.quality.bars||{})[k]||''}/>)}</div><p className="text-gray-400 text-sm mt-3">{d.quality.explanation}</p></>}
    </section>
    <section className="card">
      <h2 className="text-xl font-semibold mb-4 inline-flex items-center gap-2"><GitCompare className="w-5 h-5"/>Synergy &amp; Conflicts</h2>
      <h3 className="text-sm font-medium text-gray-300 mb-2">Synergies</h3>
      {(d.synergy?.synergies||[]).length?(d.synergy.synergies).slice(0,8).map((s:any,i:number)=><div key={i} className="text-sm text-gray-300 border-b border-surface-border py-2"><span className="text-accent">{s.score}</span> · {s.mods.join(' + ')} — {s.explanation}</div>):<p className="text-gray-500 text-sm">No strong synergies detected.</p>}
      <h3 className="text-sm font-medium text-gray-300 mt-4 mb-2">World-gen overlap warnings</h3>
      {(d.synergy?.conflicts||[]).length?(d.synergy.conflicts).slice(0,8).map((c:any,i:number)=><div key={i} className="text-sm text-yellow-400 py-1">⚠ {c.mods.join(' + ')} — {c.explanation}</div>):<p className="text-gray-500 text-sm">No overlaps flagged.</p>}
    </section>
    <section className="card">
      <h2 className="text-xl font-semibold mb-4 inline-flex items-center gap-2"><Gauge className="w-5 h-5"/>Performance Simulator</h2>
      {d.performance&&<div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div><div className="text-gray-500">RAM</div><div className="text-gray-100 text-lg">{d.performance.ram_gb} GB</div></div>
        <div><div className="text-gray-500">VRAM</div><div className="text-gray-100 text-lg">{d.performance.vram_gb} GB</div></div>
        <div><div className="text-gray-500">CPU cores</div><div className="text-gray-100 text-lg">{d.performance.cpu_cores}</div></div>
        <div><div className="text-gray-500">Expected FPS</div><div className="text-gray-100 text-lg">{d.performance.expected_fps?.low}–{d.performance.expected_fps?.high}</div></div>
        <div className="col-span-2 md:col-span-4"><div className="text-gray-500">GPU recommendation</div><div className="text-gray-100">{d.performance.gpu_recommendation}</div></div>
      </div>}
    </section>
    <section className="card">
      <h2 className="text-xl font-semibold mb-4 inline-flex items-center gap-2"><ShieldCheck className="w-5 h-5"/>Variants</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">{(d.variants||[]).map((v:any)=><div key={v.tier} className="bg-surface-overlay rounded-lg p-4"><div className="font-semibold text-gray-100">{v.name}</div><div className="text-sm text-gray-400 mt-1">{v.mods} mods · {v.ram_gb} GB · shaders {v.shaders?'on':'off'}</div></div>)}</div>
    </section>
    <section className="card">
      <h2 className="text-xl font-semibold mb-4 inline-flex items-center gap-2"><Users className="w-5 h-5"/>Mod Reputation</h2>
      <div className="space-y-1 max-h-64 overflow-y-auto">{(d.reputation||[]).map((r:any,i:number)=><div key={i} className="flex justify-between text-sm text-gray-300 border-b border-surface-border py-1"><span>{r.mod}</span><span className="text-gray-500">stability {r.stability}/5 · maint {r.maintenance}/5 · compat {r.compatibility}/5 · perf {r.performance}/5</span></div>)}</div>
    </section>
    <section className="card">
      <h2 className="text-xl font-semibold mb-3">Natural-language editor</h2>
      <p className="text-gray-400 text-sm mb-3">Describe a change. The plan is approval-gated and never removes mods automatically.</p>
      <textarea className="input min-h-[100px]" value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="maak de nachten enger..."/>
      <button className="btn btn-primary mt-3" disabled={!prompt.trim()||nl.isPending} onClick={()=>nl.mutate()}>Propose plan</button>
      {plan&&<pre className="text-sm whitespace-pre-wrap mt-4 bg-surface-overlay rounded-lg p-3">{JSON.stringify(plan,null,2)}</pre>}
    </section>
    <section className="card">
      <h2 className="text-xl font-semibold mb-3">Safe update plan</h2>
      <button className="btn btn-secondary" disabled={safeUpdate.isPending} onClick={()=>safeUpdate.mutate()}>Plan a safe update</button>
      {update&&<div className="mt-4 text-sm text-gray-300"><p className="mb-2">Backup + approval required before anything changes.</p><ol className="list-decimal ml-5 space-y-1">{(update.steps||[]).map((s:string,i:number)=><li key={i}>{s}</li>)}</ol></div>}
    </section>
  </div>;
}
