# F1 Podium Predictor

Static web app that ranks every driver’s estimated **podium probability** for each Formula 1 race, using historical telemetry from the free [OpenF1](https://openf1.org/) API (2023 onward, no authentication). The UI is a React + Vite + Tailwind frontend; all probabilities are **pre-computed in Python** at build time and shipped as JSON for hosting on **GitHub Pages** (no backend).

**Live site:** [https://chaarvigoel.github.io/f1_race_predictor/](https://chaarvigoel.github.io/f1_race_predictor/)

## How it works

1. **`scripts/generate_predictions.py`** (run in CI on every push to `main`) fetches OpenF1 data for all **Race** and **Qualifying** sessions in **2023 and 2024**, matches weekends by `meeting_key`, and builds one training row per driver per race.
2. Models are trained on **2023** races and evaluated on **2024** (classification report + ROC-AUC printed in the logs).
3. **XGBoost** probabilities are written to `frontend/public/data/predictions.json`, with `sessions.json` listing every race (sorted by date ascending). The React app loads both files at runtime.

**Rate limits:** OpenF1’s free tier is about **3 requests/second** and **30/minute**. The fetcher inserts **`time.sleep(0.4)`** between sequential requests. A full refresh touches many endpoints per driver, so a complete rebuild can take a while.

**Data floor:** OpenF1 coverage starts in **2023**; there is no supported path to earlier seasons in this pipeline.

## Features (ML)

| Feature | Source |
|--------|--------|
| `grid_position` | Qualifying position aligned to lap 1 end (fallback: last qual sample; default 20) |
| `avg_q_sector_*` | Mean sector times over all qualifying laps |
| `num_pit_stops` | Count of pit records in the race |
| `constructor_encoded` | `LabelEncoder` on team name (unknown teams mapped to a reserved bucket) |
| `driver_encoded` | F1 `driver_number` as a numeric feature |
| `avg_air_temp`, `avg_track_temp` | Session weather means |
| `rainfall` | 1 if any weather sample reports rain |
| `laps_led` | Race laps where the driver’s last position sample before lap end was P1 |

**Target:** `podium = 1` if the driver’s **final** race position (last position sample) is ≤ 3.

**Models:** **Logistic regression** (baseline, `max_iter=1000`) and **XGBoost** (`n_estimators=100`, `learning_rate=0.1`, `max_depth=4`). Both use `predict_proba[:, 1]`; the shipped JSON uses **XGBoost** by default. Artifacts are saved under `scripts/models/` with **joblib**.

## Local development

### Generate data and train (Python 3.11+)

```bash
cd scripts
pip install -r requirements.txt
python generate_predictions.py
```

This writes `frontend/public/data/sessions.json`, `frontend/public/data/predictions.json`, and model binaries under `scripts/models/`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173/f1_race_predictor/`). Without the JSON files, the app shows the **error state** until you run the generator.

### Retraining / refreshing predictions

Re-run `generate_predictions.py`, commit the updated JSON if you want it versioned, and push to `main`. CI regenerates artifacts on each deploy so the site stays in sync with the latest OpenF1 data and training code.

## Deployment (GitHub Actions)

Workflow: `.github/workflows/deploy.yml`

1. **generate** — Python installs dependencies, runs `python scripts/generate_predictions.py`, uploads `frontend/public/data/` as an artifact.
2. **build-and-deploy** — Downloads that artifact into `frontend/public/data/`, runs `npm install` and `npm run build` in `frontend/`, then publishes **`frontend/dist/`** to the **`gh-pages`** branch with [peaceiris/actions-gh-pages](https://github.com/peaceiris/actions-gh-pages).

The Vite `base` path is set to `/f1_race_predictor/` to match GitHub Pages project-site URLs.

## Repository layout

```
f1_race_predictor/
├── scripts/
│   ├── data_fetcher.py
│   ├── feature_engineering.py
│   ├── model.py
│   ├── generate_predictions.py
│   ├── requirements.txt
│   └── models/           # joblib outputs (gitignored)
├── frontend/
│   ├── public/data/      # generated JSON (artifact in CI)
│   └── src/ ...
├── .github/workflows/deploy.yml
└── README.md
```
