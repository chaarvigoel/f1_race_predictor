"""Fetch OpenF1 data, train models, write static JSON for the frontend."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from data_fetcher import fetch_race_and_qual_sessions
from feature_engineering import attach_qual_session_keys, build_session_feature_frame, _race_display_name
from model import rank_precomputed_frame, train_models

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "frontend" / "public" / "data"


def _session_record(row: pd.Series) -> dict:
    ds = row.get("date_start")
    date_str = ""
    if pd.notna(ds):
        try:
            date_str = str(pd.Timestamp(ds).date())
        except Exception:
            date_str = str(ds)[:10]
    return {
        "session_key": int(row["session_key"]),
        "race_name": _race_display_name(row),
        "year": int(row["year"]),
        "date": date_str,
    }


def main() -> int:
    years = [2023, 2024]
    races, quals = fetch_race_and_qual_sessions(years)
    if races.empty:
        print("No race sessions returned; aborting.")
        return 1

    races = races.sort_values("date_start").reset_index(drop=True)
    races = attach_qual_session_keys(races, quals)

    train_mask = races["year"] == 2023
    test_mask = races["year"] == 2024

    train_parts: list[pd.DataFrame] = []
    test_parts: list[pd.DataFrame] = []
    failed_build = 0
    frames_by_session: dict[int, pd.DataFrame] = {}

    for _, r in races.iterrows():
        sk = int(r["session_key"])
        year = int(r["year"])
        qk = r.get("qual_session_key")
        qual_key = int(qk) if pd.notna(qk) else None
        try:
            frame = build_session_feature_frame(sk, qual_key, year, include_target=True)
        except Exception as e:
            print(f"Feature build failed session_key={sk}: {e}")
            failed_build += 1
            continue
        if frame.empty:
            failed_build += 1
            continue
        frames_by_session[sk] = frame
        if year == 2023:
            train_parts.append(frame)
        elif year == 2024:
            test_parts.append(frame)

    train_df = pd.concat(train_parts, ignore_index=True) if train_parts else pd.DataFrame()
    test_df = pd.concat(test_parts, ignore_index=True) if test_parts else pd.DataFrame()

    if train_df.empty or test_df.empty:
        print("Insufficient labeled rows for train/test; aborting.")
        return 1

    artifacts = train_models(train_df, test_df)

    session_rows: list[dict] = []
    predictions_out: dict[str, list[dict]] = {}
    failed_pred = 0
    processed = 0

    for _, r in races.iterrows():
        sk = int(r["session_key"])
        rec = _session_record(r)
        session_rows.append(rec)
        frame = frames_by_session.get(sk)
        if frame is None:
            failed_pred += 1
            continue
        try:
            ranked = rank_precomputed_frame(frame, model_type="xgb", artifacts=artifacts)
        except Exception as e:
            print(f"Prediction failed session_key={sk}: {e}")
            failed_pred += 1
            continue
        if not ranked:
            failed_pred += 1
            continue
        predictions_out[str(sk)] = ranked
        processed += 1

    session_rows.sort(key=lambda x: x.get("date") or "")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "sessions.json").write_text(
        json.dumps(session_rows, indent=2), encoding="utf-8"
    )
    (DATA_DIR / "predictions.json").write_text(
        json.dumps(predictions_out, indent=2), encoding="utf-8"
    )

    print("\n=== Summary ===")
    print(f"Sessions listed: {len(session_rows)}")
    print(f"Predictions written: {processed}")
    print(f"Feature builds skipped/failed: {failed_build}")
    print(f"Predictions failed/empty: {failed_pred}")
    print(f"Logistic regression ROC-AUC (2024): {artifacts.get('lr_auc')}")
    print(f"XGBoost ROC-AUC (2024): {artifacts.get('xgb_auc')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
