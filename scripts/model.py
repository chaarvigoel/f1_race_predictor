"""Train baseline + XGBoost models and run session-level predictions."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

from data_fetcher import fetch_qualifying_for_meeting, fetch_session_by_key
from feature_engineering import build_session_feature_frame

FEATURE_COLS = [
    "grid_position",
    "avg_q_sector_1",
    "avg_q_sector_2",
    "avg_q_sector_3",
    "num_pit_stops",
    "constructor_encoded",
    "driver_encoded",
    "avg_air_temp",
    "avg_track_temp",
    "rainfall",
    "laps_led",
]

SCRIPTS_DIR = Path(__file__).resolve().parent
MODELS_DIR = SCRIPTS_DIR / "models"
ARTIFACT_NAME = "podium_artifacts.joblib"


def _models_path() -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return MODELS_DIR / ARTIFACT_NAME


def _apply_constructor_encoding(df: pd.DataFrame, enc: LabelEncoder, unknown_token: str) -> pd.Series:
    names = df["constructor_name"].fillna(unknown_token).astype(str)
    known = set(enc.classes_)
    mapped = names.where(names.isin(known), other=unknown_token)
    return pd.Series(enc.transform(mapped), index=df.index, dtype=np.int64)


def prepare_matrix(
    raw: pd.DataFrame,
    constructor_encoder: LabelEncoder | None,
    impute: dict[str, float] | None,
    fit_encoder: bool,
) -> tuple[pd.DataFrame, LabelEncoder, dict[str, float]]:
    if raw.empty:
        return raw, LabelEncoder(), {}

    df = raw.copy()
    unknown = "__unknown__"

    if fit_encoder:
        names = df["constructor_name"].fillna(unknown).astype(str)
        enc = LabelEncoder()
        enc.fit(pd.concat([names, pd.Series([unknown])], ignore_index=True).unique())
    else:
        assert constructor_encoder is not None
        enc = constructor_encoder

    df["constructor_encoded"] = _apply_constructor_encoding(df, enc, unknown)

    if impute is None:
        med: dict[str, float] = {}
        for c in ("avg_q_sector_1", "avg_q_sector_2", "avg_q_sector_3"):
            med[c] = float(df[c].median(skipna=True)) if df[c].notna().any() else 0.0
        med["avg_air_temp"] = (
            float(df["avg_air_temp"].median(skipna=True))
            if df["avg_air_temp"].notna().any()
            else 0.0
        )
        med["avg_track_temp"] = (
            float(df["avg_track_temp"].median(skipna=True))
            if df["avg_track_temp"].notna().any()
            else 0.0
        )
        impute = med

    for c in ("avg_q_sector_1", "avg_q_sector_2", "avg_q_sector_3"):
        df[c] = df[c].fillna(impute.get(c, 0.0))
    df["avg_air_temp"] = df["avg_air_temp"].fillna(impute.get("avg_air_temp", 0.0))
    df["avg_track_temp"] = df["avg_track_temp"].fillna(impute.get("avg_track_temp", 0.0))

    return df, enc, impute


def train_models(train_df: pd.DataFrame, test_df: pd.DataFrame) -> dict:
    train_clean = train_df.dropna(subset=["podium"]).copy()
    test_clean = test_df.dropna(subset=["podium"]).copy()

    train_mat, enc, impute_vals = prepare_matrix(train_clean, None, None, fit_encoder=True)
    test_mat, _, _ = prepare_matrix(test_clean, enc, impute_vals, fit_encoder=False)

    X_tr = train_mat[FEATURE_COLS].astype(np.float64)
    y_tr = train_mat["podium"].astype(int)
    X_te = test_mat[FEATURE_COLS].astype(np.float64)
    y_te = test_mat["podium"].astype(int)

    lr = LogisticRegression(max_iter=1000)
    lr.fit(X_tr, y_tr)

    xgb = XGBClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=4,
        random_state=42,
        eval_metric="logloss",
    )
    xgb.fit(X_tr, y_tr)

    lr_auc = float("nan")
    xgb_auc = float("nan")
    for name, model, auc_holder in [
        ("logistic_regression", lr, "lr"),
        ("xgboost", xgb, "xgb"),
    ]:
        proba = model.predict_proba(X_te)[:, 1]
        pred = (proba >= 0.5).astype(int)
        print(f"\n=== {name} — 2024 holdout ===")
        print(classification_report(y_te, pred, zero_division=0))
        try:
            auc = roc_auc_score(y_te, proba)
            print(f"ROC-AUC: {auc:.4f}")
        except ValueError as e:
            print(f"ROC-AUC: n/a ({e})")
            auc = float("nan")
        if auc_holder == "lr":
            lr_auc = auc
        else:
            xgb_auc = auc

    artifacts = {
        "lr": lr,
        "xgb": xgb,
        "constructor_encoder": enc,
        "impute": impute_vals,
        "feature_cols": FEATURE_COLS,
        "lr_auc": lr_auc,
        "xgb_auc": xgb_auc,
    }
    joblib.dump(artifacts, _models_path())
    return artifacts


def load_artifacts() -> dict:
    path = _models_path()
    if not path.exists():
        raise FileNotFoundError(f"Missing model artifacts at {path}. Train models first.")
    return joblib.load(path)


def rank_precomputed_frame(
    raw: pd.DataFrame,
    model_type: str = "xgb",
    artifacts: dict | None = None,
) -> list[dict]:
    if raw.empty:
        return []
    if artifacts is None:
        artifacts = load_artifacts()
    infer = raw.drop(columns=["podium"], errors="ignore").copy()
    mat, _, _ = prepare_matrix(
        infer,
        artifacts["constructor_encoder"],
        artifacts["impute"],
        fit_encoder=False,
    )
    X = mat[FEATURE_COLS].astype(np.float64)
    mdl = artifacts["lr"] if model_type == "lr" else artifacts["xgb"]
    proba = mdl.predict_proba(X)[:, 1]
    out = mat.assign(podium_probability=proba)[
        ["driver_name", "team", "driver_number", "podium_probability"]
    ].sort_values("podium_probability", ascending=False)
    return json.loads(out.to_json(orient="records", double_precision=8))


def predict_session(
    session_key: int,
    qual_session_key: int | None,
    year: int,
    model_type: str = "xgb",
    artifacts: dict | None = None,
) -> list[dict]:
    if artifacts is None:
        artifacts = load_artifacts()

    raw = build_session_feature_frame(
        race_session_key=session_key,
        qual_session_key=qual_session_key,
        year=year,
        include_target=False,
    )
    return rank_precomputed_frame(raw, model_type=model_type, artifacts=artifacts)


def predict(session_key: int, model_type: str = "xgb") -> list[dict]:
    """Resolve meeting/year via OpenF1, engineer features, return ranked driver probabilities."""
    meta = fetch_session_by_key(session_key)
    if meta.empty:
        return []
    row = meta.iloc[0]
    if str(row.get("session_type", "")) != "Race":
        return []
    meeting_key = int(row["meeting_key"])
    year = int(row["year"])
    qual_df = fetch_qualifying_for_meeting(meeting_key, year)
    qual_key = int(qual_df.iloc[0]["session_key"]) if not qual_df.empty else None
    artifacts = load_artifacts()
    return predict_session(session_key, qual_key, year, model_type, artifacts)
