import { useState } from 'react';
import { HelpCircle } from 'lucide-react';

/**
 * A small "?" icon that reveals explanatory text on hover/focus/click.
 * Click toggles it (keeps it open on touch devices); hover shows it on desktop.
 */
const HelpTip = ({ text, title }: { text: string; title?: string }) => {
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-flex items-center align-middle">
      <button
        type="button"
        aria-label={title ? `Help: ${title}` : 'Help'}
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className="text-gray-500 hover:text-accent focus:text-accent focus:outline-none"
      >
        <HelpCircle className="w-4 h-4" />
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute left-5 top-0 z-20 w-72 rounded-lg border border-surface-border bg-surface-raised p-3 text-xs text-gray-300 shadow-xl whitespace-pre-line"
        >
          {title && <span className="block font-semibold text-gray-100 mb-1">{title}</span>}
          {text}
        </span>
      )}
    </span>
  );
};

export default HelpTip;
