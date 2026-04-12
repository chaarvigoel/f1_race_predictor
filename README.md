# F1 Podium Predictor

Static web app that ranks every driver’s estimated **podium probability** for each Formula 1 race, using historical telemetry from the free [OpenF1](https://openf1.org/) API (2023 onward, no authentication). The UI is a React + Vite + Tailwind frontend; all probabilities are **pre-computed in Python** at build time and shipped as JSON for hosting on **GitHub Pages** (no backend).

**Live site:** [https://chaarvigoel.github.io/f1_race_predictor/](https://chaarvigoel.github.io/f1_race_predictor/)

## How it works

1. **`scripts/generate_predictions.py`** (run in CI on every push to `main`) fetches OpenF1 data for all **Race** and **Qualifying** sessions in **2023 and 2024**, matches weekends by `meeting_key`, and builds one training row per driver per race.
2. Models are trained on **2023** races and evaluated on **2024** (classification report + ROC-AUC printed in the logs).
3. **XGBoost** probabilities are written to `frontend/public/data/predictions.json`, with `sessions.json` listing every race (sorted by date ascending). The React app loads both files at runtime.

**Rate limits:** The free tier is roughly **~30 requests/minute** (burst limits also apply). The fetcher defaults to **`2.0` seconds** between requests (`OPENF1_REQUEST_GAP_S`) and **retries on 429 / 5xx** so long runs don’t silently get empty JSON. Faster pacing (e.g. `0.4s`) often triggers **HTTP 429** → empty `drivers` lists. Override: `export OPENF1_REQUEST_GAP_S=0.4` at your own risk. Full rebuilds take **much longer** with safe pacing.

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

**Faster local test runs (scaled pipeline):** Training still needs both **2023** (train) and **2024** (holdout) in the loop.

```bash
export F1_MAX_RACES_PER_YEAR=2   # e.g. 2 earliest races per year → ~4 races, far fewer API calls
export OPENF1_REQUEST_GAP_S=1    # optional; smaller gap OK only with a tiny race cap (429 risk)
python scripts/generate_predictions.py
```

- `F1_YEARS` — optional, default `2023,2024` (comma-separated). Using only one year will fail the train/test split unless you change the script.
- `F1_MAX_RACES_PER_YEAR` — unset for full seasons.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (with the current Vite config this is usually `http://localhost:5173/` — dev uses base `/` so `public/data/*.json` is loaded from `/data/...`). Without the JSON files, the app shows the **error state** until you run the generator.

### Retraining / refreshing predictions

Re-run `generate_predictions.py`, commit the updated JSON if you want it versioned, and push to `main`. CI regenerates artifacts on each deploy so the site stays in sync with the latest OpenF1 data and training code.

## Deployment (GitHub Actions)

Workflow: `.github/workflows/deploy.yml`

1. **build** — Runs `python scripts/generate_predictions.py` (writes JSON under `frontend/public/data/`), then `npm install` and `npm run build` in `frontend/`.
2. **deploy** — Publishes **`frontend/dist/`** with GitHub’s official [Pages deployment](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site#publishing-with-a-custom-github-actions-workflow) (`upload-pages-artifact` + `deploy-pages`). No **`gh-pages`** branch.

**One-time repo setting:** **Settings → Pages → Build and deployment → Source:** choose **GitHub Actions** (not “Deploy from a branch”). If Source is still **main** / **root**, GitHub will show your **README** instead of the app at [https://chaarvigoel.github.io/f1_race_predictor/](https://chaarvigoel.github.io/f1_race_predictor/).

The Vite `base` path is `/f1_race_predictor/` so asset URLs match the project site path.

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
