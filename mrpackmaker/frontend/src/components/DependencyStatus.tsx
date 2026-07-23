import { Check, Loader2, AlertTriangle } from 'lucide-react';
export default function DependencyStatus({ report, repairing=false }: { report?: any; repairing?: boolean }) {
  if (repairing) return <div className="p-3 rounded bg-yellow-900/20 text-yellow-300 flex gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Dependency repair running...</div>;
  const errors = report?.errors?.filter((e: string) => e.toLowerCase().includes('depend')) ?? [];
  if (errors.length) return <div className="p-3 rounded bg-red-900/20 text-red-300 flex gap-2"><AlertTriangle className="w-4 h-4" /> {errors[0]}</div>;
  const count = report?.dependencies?.filter((d: any) => d.status === 'ok').length ?? 0;
  return <div className="p-3 rounded bg-green-900/20 text-green-300 flex gap-2"><Check className="w-4 h-4" /> All required dependencies resolved{count ? ` (${count} libraries)` : ''}</div>;
}
