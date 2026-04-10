const PODIUM_STYLES = [
  {
    label: 'P1',
    border: 'border-amber-400/60',
    bg: 'bg-gradient-to-b from-amber-500/25 to-amber-900/10',
    accent: 'text-amber-300',
  },
  {
    label: 'P2',
    border: 'border-slate-300/50',
    bg: 'bg-gradient-to-b from-slate-400/20 to-slate-800/10',
    accent: 'text-slate-200',
  },
  {
    label: 'P3',
    border: 'border-orange-700/50',
    bg: 'bg-gradient-to-b from-orange-700/25 to-orange-950/10',
    accent: 'text-orange-300',
  },
];

function formatPct(p) {
  if (typeof p !== 'number' || Number.isNaN(p)) return '—';
  return `${(p * 100).toFixed(1)}%`;
}

export default function PodiumCard({ drivers }) {
  const top3 = drivers.slice(0, 3);
  const maxProb = Math.max(...drivers.map((d) => d.podium_probability || 0), 1e-9);

  return (
    <div className="space-y-10">
      <section>
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-widest text-f1red">
          Predicted podium
        </h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {top3.map((d, i) => {
            const style = PODIUM_STYLES[i] ?? PODIUM_STYLES[2];
            return (
              <div
                key={d.driver_number}
                className={`rounded-xl border ${style.border} ${style.bg} p-5 shadow-lg`}
              >
                <p className={`text-xs font-bold ${style.accent}`}>{style.label}</p>
                <p className="mt-2 text-lg font-semibold leading-tight">{d.driver_name}</p>
                <p className="mt-1 text-sm text-white/60">{d.team}</p>
                <p className="mt-4 text-2xl font-bold tabular-nums text-white">
                  {formatPct(d.podium_probability)}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-widest text-white/45">
          Full grid
        </h2>
        <div className="overflow-hidden rounded-xl border border-white/10">
          <ul className="divide-y divide-white/5">
            {drivers.map((d, idx) => {
              const pct = typeof d.podium_probability === 'number' ? d.podium_probability : 0;
              const width = Math.min(100, Math.max(4, (pct / maxProb) * 100));
              const stripe = idx % 2 === 0 ? 'bg-white/[0.03]' : 'bg-transparent';
              return (
                <li
                  key={d.driver_number}
                  className={`flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:gap-4 ${stripe}`}
                >
                  <span className="w-8 shrink-0 text-sm font-medium text-white/40">{idx + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0">
                      <span className="font-medium text-white">{d.driver_name}</span>
                      <span className="text-sm text-white/50">{d.team}</span>
                    </div>
                    <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full bg-f1red transition-[width] duration-500"
                        style={{ width: `${width}%` }}
                      />
                    </div>
                  </div>
                  <span className="shrink-0 text-right text-sm font-semibold tabular-nums text-white/90 sm:w-16">
                    {formatPct(pct)}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      </section>
    </div>
  );
}
