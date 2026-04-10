import { useEffect, useMemo, useState } from 'react';
import RaceSelector from './components/RaceSelector.jsx';
import PodiumCard from './components/PodiumCard.jsx';

function sortSessionsNewestFirst(list) {
  return [...list].sort((a, b) => {
    const da = a.date || '';
    const db = b.date || '';
    return db.localeCompare(da);
  });
}

export default function App() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [predictions, setPredictions] = useState({});
  const [selectedKey, setSelectedKey] = useState(null);

  const sortedSessions = useMemo(
    () => sortSessionsNewestFirst(sessions),
    [sessions]
  );

  useEffect(() => {
    let cancelled = false;
    const base = import.meta.env.BASE_URL;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [sRes, pRes] = await Promise.all([
          fetch(`${base}data/sessions.json`),
          fetch(`${base}data/predictions.json`),
        ]);
        if (!sRes.ok || !pRes.ok) {
          throw new Error(
            'Could not load prediction data. Run the Python pipeline or check deployment artifacts.'
          );
        }
        let sessionsRaw;
        let predictionsRaw;
        try {
          sessionsRaw = await sRes.json();
        } catch {
          throw new Error('sessions.json is missing or not valid JSON.');
        }
        try {
          predictionsRaw = await pRes.json();
        } catch {
          throw new Error('predictions.json is missing or not valid JSON.');
        }
        if (!Array.isArray(sessionsRaw)) {
          throw new Error('sessions.json must contain an array of races.');
        }
        if (
          typeof predictionsRaw !== 'object' ||
          predictionsRaw === null ||
          Array.isArray(predictionsRaw)
        ) {
          throw new Error('predictions.json must be an object keyed by session_key.');
        }
        if (!cancelled) {
          setSessions(sessionsRaw);
          setPredictions(predictionsRaw);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Something went wrong loading data.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (sortedSessions.length === 0) return;
    setSelectedKey((prev) => {
      if (prev != null && sortedSessions.some((s) => s.session_key === prev)) {
        return prev;
      }
      return sortedSessions[0].session_key;
    });
  }, [sortedSessions]);

  const selectedDrivers =
    selectedKey != null ? predictions[String(selectedKey)] ?? null : null;

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-appbg">
        <div className="flex flex-col items-center gap-4">
          <div
            className="h-12 w-12 animate-spin rounded-full border-2 border-white/20 border-t-f1red"
            aria-hidden
          />
          <p className="text-sm text-white/70">Loading race data…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-appbg px-4 py-16">
        <div className="mx-auto max-w-lg rounded-xl border border-white/10 bg-white/5 p-8 text-center">
          <h1 className="text-lg font-semibold text-f1red">Unable to load data</h1>
          <p className="mt-3 text-sm leading-relaxed text-white/80">{error}</p>
        </div>
      </div>
    );
  }

  if (sortedSessions.length === 0) {
    return (
      <div className="min-h-screen bg-appbg px-4 py-16 text-center text-white/70">
        No races found in sessions.json.
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-appbg text-white">
      <header className="border-b border-white/10 bg-black/40 px-4 py-6 sm:px-8">
        <div className="mx-auto max-w-4xl">
          <p className="text-xs font-medium uppercase tracking-widest text-f1red">
            OpenF1 · Static build
          </p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">
            F1 Podium Predictor
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-white/65">
            Pre-computed podium probabilities from qualifying pace, grid, weather, pit stops, and
            laps led (2023–2024 seasons).
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-8">
        <div className="mb-8">
          <label
            htmlFor="race-select"
            className="mb-2 block text-xs font-medium uppercase tracking-wide text-white/50"
          >
            Race
          </label>
          <RaceSelector
            id="race-select"
            sessions={sortedSessions}
            value={selectedKey}
            onChange={setSelectedKey}
          />
        </div>

        {selectedDrivers && selectedDrivers.length > 0 ? (
          <PodiumCard drivers={selectedDrivers} />
        ) : (
          <div className="rounded-xl border border-white/10 bg-white/5 p-8 text-center text-white/65">
            No predictions available for this session.
          </div>
        )}
      </main>
    </div>
  );
}
