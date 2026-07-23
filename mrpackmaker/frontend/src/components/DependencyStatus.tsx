import { Check, Loader2, AlertTriangle } from 'lucide-react';

type DependencyStatusProps = { report?: { errors?: string[]; dependencies?: Array<{ status?: string }>; mods?: Array<unknown> }; repairing?: boolean; repairedCount?: number };

export default function DependencyStatus({ report, repairing = false, repairedCount = 0 }: DependencyStatusProps) {
  if (repairing) return <div className="p-3 rounded bg-yellow-900/20 text-yellow-300 flex gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Fixing dependencies...</div>;
  const errors = report?.errors?.filter(error => error.toLowerCase().includes('depend')) ?? [];
  if (errors.length) return <div className="p-3 rounded bg-red-900/20 text-red-300 flex gap-2"><AlertTriangle className="w-4 h-4 shrink-0" /><span>{errors[0]}</span></div>;
  const libraries = report?.dependencies?.filter(item => item.status === 'ok').length ?? 0;
  const mods = report?.mods?.length ?? 0;
  return <div className="p-3 rounded bg-green-900/20 text-green-300 flex gap-2"><Check className="w-4 h-4 shrink-0" /><span>All required dependencies resolved{mods ? `, ${mods} mods` : ''}{libraries ? `, ${libraries} libraries` : ''}{repairedCount ? `. Automatically repaired ${repairedCount}` : ''}</span></div>;
}
