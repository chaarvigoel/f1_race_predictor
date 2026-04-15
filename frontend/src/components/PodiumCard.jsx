import constructorColors from '../utils/constructorColors.js';

/** Desktop render order: P2 (left), P1 (center), P3 (right). Indices map to probability-sorted top3. */
const PODIUM_SLOTS = [
  {
    place: 2,
    dataIndex: 1,
    blockH: 52,
    blockBg: '#C0C0C0',
    accent: '#C0C0C0',
    nameClass: 'text-xl font-semibold leading-tight',
    cardPad: 'px-5 py-6',
    cardFlex: 'sm:flex-1 sm:min-w-0 sm:max-w-[220px]',
    smOrder: 'sm:order-none',
    mobileOrder: 'order-2',
  },
  {
    place: 1,
    dataIndex: 0,
    blockH: 80,
    blockBg: '#FFD700',
    accent: '#FFD700',
    nameClass: 'text-[2rem] font-bold leading-tight',
    cardPad: 'px-7 py-8',
    cardFlex: 'sm:flex-[1.35] sm:min-w-0 sm:max-w-[280px]',
    smOrder: 'sm:order-none',
    mobileOrder: 'order-1',
  },
  {
    place: 3,
    dataIndex: 2,
    blockH: 32,
    blockBg: '#CD7F32',
    accent: '#CD7F32',
    nameClass: 'text-lg font-semibold leading-tight',
    cardPad: 'px-5 py-6',
    cardFlex: 'sm:flex-1 sm:min-w-0 sm:max-w-[220px]',
    smOrder: 'sm:order-none',
    mobileOrder: 'order-3',
  },
];

const GRID_MEDALS = [{ border: '#FFD700' }, { border: '#C0C0C0' }, { border: '#CD7F32' }];

function teamColor(team) {
  if (typeof team !== 'string') return '#666';
  return constructorColors[team] ?? '#666';
}

function formatPct(p) {
  if (typeof p !== 'number' || Number.isNaN(p)) return '—';
  return `${(p * 100).toFixed(1)}%`;
}

function probabilityStyle(p, accentHex) {
  if (typeof p !== 'number' || Number.isNaN(p)) return { color: '#999' };
  if (p >= 0.8) return { color: accentHex };
  if (p >= 0.5) return { color: '#ffffff' };
  return { color: '#999' };
}

const sectionLabelClass =
  'mb-3 border-l-2 border-l-[#e10600] pl-2 text-[0.65rem] font-semibold uppercase tracking-[0.15em] text-[#666]';

function PodiumColumn({ slot, driver }) {
  const tc = driver ? teamColor(driver.team) : '#666';
  const pct =
    driver && typeof driver.podium_probability === 'number' ? driver.podium_probability : NaN;
  const probStyle = probabilityStyle(pct, slot.accent);

  return (
    <div
      className={`flex w-full flex-col ${slot.cardFlex} ${slot.smOrder} ${slot.mobileOrder}`}
    >
      <div
        className={`shadow-lg ${slot.cardPad} rounded-t-xl rounded-b-none border-l-4 bg-[#141414]`}
        style={{
          borderLeftColor: tc,
          backgroundImage: `radial-gradient(ellipse 120% 80% at 50% 0%, ${slot.accent}14 0%, transparent 65%)`,
        }}
      >
        {driver ? (
          <>
            <p className={`text-white ${slot.nameClass}`}>{driver.driver_name}</p>
            <p className="mt-1 text-sm text-white/60">
              <span className="inline-flex items-center gap-1.5">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: tc }}
                  aria-hidden
                />
                {driver.team}
              </span>
            </p>
            <p className="mt-4 text-2xl font-bold tabular-nums" style={probStyle}>
              {formatPct(driver.podium_probability)}
            </p>
          </>
        ) : (
          <p className="text-sm text-white/35">—</p>
        )}
      </div>
      <div
        className="flex w-full shrink-0 items-center justify-center font-bold leading-none text-[#111]"
        style={{ height: slot.blockH, backgroundColor: slot.blockBg }}
      >
        <span className="text-[1.5rem]">{slot.place}</span>
      </div>
    </div>
  );
}

export default function PodiumCard({ drivers }) {
  const top3 = drivers.slice(0, 3);

  return (
    <div className="space-y-12">
      <section>
        <h2 className={sectionLabelClass}>Predicted podium</h2>

        {/* Mobile: P1, P2, P3 stacked (order-*). Desktop: P2 | P1 | P3, blocks bottom-aligned. */}
        <div className="flex max-w-4xl flex-col gap-4 sm:mx-auto sm:flex-row sm:items-end sm:justify-center sm:gap-3 md:gap-4">
          {PODIUM_SLOTS.map((slot) => {
            const driver = top3[slot.dataIndex];
            return (
              <PodiumColumn
                key={`podium-${slot.place}`}
                slot={slot}
                driver={driver}
              />
            );
          })}
        </div>
      </section>

      <section>
        <h2 className={sectionLabelClass}>Full grid</h2>
        <div className="overflow-hidden rounded-xl border border-white/10">
          <ul className="divide-y-0">
            {drivers.map((d, idx) => {
              const pct = typeof d.podium_probability === 'number' ? d.podium_probability : 0;
              const width = Math.min(100, Math.max(0, pct <= 1 ? pct * 100 : pct));
              const tc = teamColor(d.team);
              const barColor = constructorColors[d.team] ?? '#e10600';
              const isPodiumRow = idx < 3;
              const medal = GRID_MEDALS[idx];
              const rowBg = isPodiumRow
                ? 'bg-[#1e1e1e]'
                : idx % 2 === 0
                  ? 'bg-white/[0.03]'
                  : 'bg-transparent';
              const borderBottom =
                idx < drivers.length - 1 && idx >= 2 ? 'border-b border-[#1f1f1f]' : '';
              return (
                <li
                  key={d.driver_number}
                  className={`flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:gap-4 ${rowBg} ${borderBottom}`}
                  style={
                    isPodiumRow
                      ? { borderLeft: `3px solid ${medal.border}` }
                      : { borderLeft: '3px solid transparent' }
                  }
                >
                  <span
                    className={`w-8 shrink-0 text-sm font-medium ${isPodiumRow ? 'text-white/55' : 'text-white/40'}`}
                  >
                    {idx + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-0">
                      <span
                        className={`font-medium ${isPodiumRow ? 'text-white' : 'text-white/90'}`}
                      >
                        {d.driver_name}
                      </span>
                      <span className="inline-flex items-center gap-1.5 text-sm text-white/50">
                        <span
                          className="h-2.5 w-2.5 shrink-0 rounded-full"
                          style={{ backgroundColor: tc }}
                          aria-hidden
                        />
                        {d.team}
                      </span>
                    </div>
                    <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full transition-[width] duration-500"
                        style={{ width: `${width}%`, backgroundColor: barColor }}
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
