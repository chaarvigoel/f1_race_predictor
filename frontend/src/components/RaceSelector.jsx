export default function RaceSelector({ id, sessions, value, onChange }) {
  return (
    <select
      id={id}
      className="w-full max-w-xl cursor-pointer rounded-lg border border-white/15 bg-black/50 px-4 py-3 text-sm text-white outline-none ring-f1red transition focus:border-f1red focus:ring-2"
      value={value ?? ''}
      onChange={(e) => onChange(Number(e.target.value))}
    >
      {sessions.map((s) => (
        <option key={s.session_key} value={s.session_key}>
          {s.year} — {s.race_name}
        </option>
      ))}
    </select>
  );
}
