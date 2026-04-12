"""Build per-(driver, race) feature rows as pandas DataFrames."""

from __future__ import annotations

import numpy as np
import pandas as pd

from data_fetcher import (
    fetch_drivers,
    fetch_laps,
    fetch_pit,
    fetch_position,
    fetch_weather,
)

SECTOR_COLS = ("duration_sector_1", "duration_sector_2", "duration_sector_3")


def _laps_usable_for_sequence(laps_df: pd.DataFrame) -> bool:
    """OpenF1 may return [] (empty frame, no columns) or rows missing lap_number."""
    return (
        not laps_df.empty
        and "lap_number" in laps_df.columns
        and "date_start" in laps_df.columns
    )


def _parse_dt(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def _race_display_name(row: pd.Series) -> str:
    country = row.get("country_name")
    if pd.notna(country) and str(country).strip():
        return f"{country} Grand Prix"
    loc = row.get("location")
    if pd.notna(loc) and str(loc).strip():
        return f"{loc} Grand Prix"
    return "Grand Prix"


def attach_qual_session_keys(races: pd.DataFrame, quals: pd.DataFrame) -> pd.DataFrame:
    if races.empty or quals.empty:
        return races.assign(qual_session_key=pd.NA)
    q = quals[["meeting_key", "session_key"]].rename(columns={"session_key": "qual_session_key"})
    merged = races.merge(q, on="meeting_key", how="left")
    return merged


def _grid_from_qual(
    driver_number: int,
    qual_pos: pd.DataFrame,
    qual_laps_driver: pd.DataFrame,
) -> float:
    default = 20.0
    if qual_pos.empty:
        return default
    dpos = qual_pos[qual_pos["driver_number"] == driver_number].copy()
    if dpos.empty:
        return default
    dpos["date"] = _parse_dt(dpos["date"])
    dpos = dpos.dropna(subset=["date"])
    if dpos.empty:
        return default

    lap1 = pd.DataFrame()
    if _laps_usable_for_sequence(qual_laps_driver):
        lap1 = qual_laps_driver[
            pd.to_numeric(qual_laps_driver["lap_number"], errors="coerce") == 1
        ]
    if not lap1.empty:
        lap1 = lap1.iloc[0]
        start = _parse_dt(pd.Series([lap1.get("date_start")])).iloc[0]
        dur = lap1.get("lap_duration")
        if pd.notna(start) and pd.notna(dur):
            try:
                end = start + pd.Timedelta(seconds=float(dur))
            except (TypeError, ValueError):
                end = None
            if end is not None:
                window = dpos[dpos["date"] <= end]
                if not window.empty:
                    row = window.sort_values("date").iloc[-1]
                    return float(row["position"])

    last = dpos.sort_values("date").iloc[-1]
    return float(last["position"])


def _avg_sectors(qual_laps_driver: pd.DataFrame) -> tuple[float, float, float]:
    if qual_laps_driver.empty:
        return (np.nan, np.nan, np.nan)
    out: list[float] = []
    for col in SECTOR_COLS:
        if col not in qual_laps_driver.columns:
            out.append(np.nan)
            continue
        s = pd.to_numeric(qual_laps_driver[col], errors="coerce")
        out.append(float(s.mean(skipna=True)) if s.notna().any() else np.nan)
    return (out[0], out[1], out[2])


def _count_laps_led(
    driver_number: int,
    race_laps_driver: pd.DataFrame,
    race_pos_driver: pd.DataFrame,
) -> int:
    if race_pos_driver.empty or not _laps_usable_for_sequence(race_laps_driver):
        return 0
    laps = race_laps_driver.copy()
    laps["_lap_ord"] = pd.to_numeric(laps["lap_number"], errors="coerce")
    laps = laps.sort_values("_lap_ord", na_position="last")
    laps["date_start"] = _parse_dt(laps["date_start"])
    laps["lap_duration"] = pd.to_numeric(laps["lap_duration"], errors="coerce")
    pos = race_pos_driver.copy()
    pos["date"] = _parse_dt(pos["date"])
    pos = pos.dropna(subset=["date"])
    if pos.empty:
        return 0

    led = 0
    for i, lap in laps.iterrows():
        t0 = lap["date_start"]
        dur = lap["lap_duration"]
        if pd.isna(t0):
            continue
        if pd.notna(dur):
            try:
                t_end = t0 + pd.Timedelta(seconds=float(dur))
            except (TypeError, ValueError):
                t_end = t0
        else:
            t_end = t0
        snap = pos[pos["date"] <= t_end]
        if snap.empty:
            continue
        last_p = snap.sort_values("date").iloc[-1]["position"]
        try:
            if int(last_p) == 1:
                led += 1
        except (TypeError, ValueError):
            continue
    return led


def _final_race_position(driver_number: int, race_pos: pd.DataFrame) -> float | None:
    d = race_pos[race_pos["driver_number"] == driver_number].copy()
    if d.empty:
        return None
    d["date"] = _parse_dt(d["date"])
    d = d.dropna(subset=["date"])
    if d.empty:
        return None
    last = d.sort_values("date").iloc[-1]
    try:
        return float(last["position"])
    except (TypeError, ValueError):
        return None


def build_session_feature_frame(
    race_session_key: int,
    qual_session_key: int | None,
    year: int,
    include_target: bool,
) -> pd.DataFrame:
    drivers_df = fetch_drivers(race_session_key)
    if drivers_df.empty or "driver_number" not in drivers_df.columns:
        return pd.DataFrame()

    pit_df = fetch_pit(race_session_key)
    race_pos_df = fetch_position(race_session_key)
    weather_df = fetch_weather(race_session_key)

    qual_pos_df = pd.DataFrame()
    if qual_session_key is not None and not pd.isna(qual_session_key):
        qual_pos_df = fetch_position(int(qual_session_key))

    if weather_df.empty:
        avg_air = np.nan
        avg_track = np.nan
        rainfall = 0
    else:
        air = pd.to_numeric(weather_df.get("air_temperature"), errors="coerce")
        track = pd.to_numeric(weather_df.get("track_temperature"), errors="coerce")
        avg_air = float(air.mean(skipna=True)) if air.notna().any() else np.nan
        avg_track = float(track.mean(skipna=True)) if track.notna().any() else np.nan
        rf = weather_df.get("rainfall")
        if rf is None:
            rainfall = 0
        else:
            num = pd.to_numeric(rf, errors="coerce").fillna(0)
            rainfall = 1 if (num > 0).any() or (rf == True).any() else 0

    rows: list[pd.DataFrame] = []
    for _, drv in drivers_df.iterrows():
        dnum = int(drv["driver_number"])
        team = str(drv.get("team_name", "") or "")

        num_pits = 0
        if not pit_df.empty and "driver_number" in pit_df.columns:
            num_pits = int((pit_df["driver_number"] == dnum).sum())

        qual_laps_d = (
            fetch_laps(int(qual_session_key), dnum)
            if qual_session_key is not None and not pd.isna(qual_session_key)
            else pd.DataFrame()
        )
        race_laps_d = fetch_laps(race_session_key, dnum)

        grid = (
            _grid_from_qual(dnum, qual_pos_df, qual_laps_d)
            if qual_session_key is not None and not pd.isna(qual_session_key)
            else 20.0
        )
        s1, s2, s3 = _avg_sectors(qual_laps_d)

        rpos_d = (
            race_pos_df[race_pos_df["driver_number"] == dnum]
            if not race_pos_df.empty
            else pd.DataFrame()
        )
        laps_led = _count_laps_led(dnum, race_laps_d, rpos_d)

        first = str(drv.get("first_name", "") or "").strip()
        last = str(drv.get("last_name", "") or "").strip()
        driver_name = f"{first} {last}".strip() or str(drv.get("full_name", "") or "")

        row = {
            "session_key": race_session_key,
            "year": year,
            "driver_number": dnum,
            "driver_name": driver_name,
            "team": team,
            "grid_position": grid,
            "avg_q_sector_1": s1,
            "avg_q_sector_2": s2,
            "avg_q_sector_3": s3,
            "num_pit_stops": num_pits,
            "constructor_name": team,
            "driver_encoded": float(dnum),
            "avg_air_temp": avg_air,
            "avg_track_temp": avg_track,
            "rainfall": rainfall,
            "laps_led": laps_led,
        }
        if include_target:
            fin = _final_race_position(dnum, race_pos_df)
            row["podium"] = int(fin is not None and fin <= 3) if fin is not None else np.nan
        rows.append(pd.DataFrame([row]))

    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
