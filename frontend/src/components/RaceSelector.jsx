/** Session keys must stay strings to match predictions.json and <select> DOM values. */
export default function RaceSelector({ id, sessions, value, onChange }) {
  return (
    <select
      id={id}
      className="w-full max-w-xl cursor-pointer rounded-lg border border-white/15 bg-black/50 px-4 py-3 text-sm text-white outline-none ring-f1red transition focus:border-f1red focus:ring-2"
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value)}
    >
      {sessions.map((s) => {
        const sk = String(s.session_key);
        return (
          <option key={sk} value={sk}>
            {s.year} — {s.race_name}
          </option>
        );
      })}
    </select>
  );
}
