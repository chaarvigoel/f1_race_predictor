import { useEffect, useRef, useState } from 'react';

function Chevron({ open }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 text-white/50 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
      aria-hidden
    >
      <path
        d="M4 6L8 10L12 6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Session keys stay strings to match predictions.json keys. */
export default function RaceDropdown({ id, sessions, value, onChange }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  const selected = sessions.find((s) => String(s.session_key) === String(value ?? ''));
  const label = selected
    ? `${selected.year} — ${selected.race_name}`
    : 'Select a race';

  useEffect(() => {
    function handlePointerDown(e) {
      if (!rootRef.current?.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, []);

  return (
    <div ref={rootRef} className="relative w-full max-w-xl">
      <button
        type="button"
        id={id}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 rounded-lg border border-[#333] bg-[#1a1a1a] px-4 py-3 text-left text-sm text-white outline-none ring-f1red transition focus-visible:ring-2"
      >
        <span className="min-w-0 truncate">{label}</span>
        <Chevron open={open} />
      </button>

      <div
        className={`absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden rounded-lg border border-[#333] bg-[#1a1a1a] shadow-xl transition-[opacity,transform] duration-200 ease-out ${
          open
            ? 'pointer-events-auto translate-y-0 opacity-100'
            : 'pointer-events-none -translate-y-1 opacity-0'
        }`}
      >
        <ul
          role="listbox"
          aria-labelledby={id}
          className="max-h-[300px] overflow-y-auto py-1"
        >
          {sessions.map((s) => {
            const sk = String(s.session_key);
            const isSelected = String(value ?? '') === sk;
            return (
              <li key={sk} role="presentation">
                <button
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => {
                    onChange(sk);
                    setOpen(false);
                  }}
                  className={`flex w-full border-l-[3px] py-2.5 pl-4 pr-4 text-left text-sm text-white transition-colors hover:bg-[#2a2a2a] ${
                    isSelected ? 'border-l-[#e10600]' : 'border-l-transparent'
                  }`}
                >
                  {s.year} — {s.race_name}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
