"""OpenF1 API client. All requests are sequential with rate limiting."""

from __future__ import annotations

import os
import time
from typing import Any

import pandas as pd
import requests

BASE = "https://api.openf1.org/v1"
# Free tier is ~30 requests/minute; 0.4s (~150/min) triggers mass 429 → empty JSON in practice.
# Use >=2s between calls for sustained crawls. Override: export OPENF1_REQUEST_GAP_S=0.4
REQUEST_GAP_S = float(os.environ.get("OPENF1_REQUEST_GAP_S", "2.0"))
MAX_RETRIES = int(os.environ.get("OPENF1_MAX_RETRIES", "5"))


def _request_json(url: str) -> list[dict[str, Any]]:
    for attempt in range(MAX_RETRIES):
        time.sleep(REQUEST_GAP_S)
        try:
            resp = requests.get(url, timeout=90)
            if resp.status_code == 429:
                wait_s = int(resp.headers.get("Retry-After", "30"))
                wait_s = min(max(wait_s, 5), 120)
                if os.environ.get("OPENF1_DEBUG"):
                    print(f"[OpenF1] 429, sleeping {wait_s}s then retry {attempt + 1}/{MAX_RETRIES} {url[:80]}...")
                time.sleep(wait_s)
                continue
            if resp.status_code in (502, 503, 504):
                if os.environ.get("OPENF1_DEBUG"):
                    print(f"[OpenF1] {resp.status_code} retry {attempt + 1}/{MAX_RETRIES}")
                time.sleep(5 + attempt * 5)
                continue
            # OpenF1 returns 404 + {"detail":"No results found."} when a session exists
            # but has no rows (e.g. cancelled 2023 Imola). Do not burn retries on that.
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            return []
        except requests.RequestException:
            if attempt + 1 >= MAX_RETRIES:
                return []
            time.sleep(3 + attempt * 3)
            continue
        except (ValueError, TypeError):
            return []
    return []


def _records_to_df(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def fetch_sessions(session_type: str, year: int) -> pd.DataFrame:
    url = f"{BASE}/sessions?session_type={session_type}&year={year}"
    return _records_to_df(_request_json(url))


def fetch_laps(session_key: int, driver_number: int) -> pd.DataFrame:
    url = f"{BASE}/laps?session_key={session_key}&driver_number={driver_number}"
    return _records_to_df(_request_json(url))


def fetch_pit(session_key: int) -> pd.DataFrame:
    url = f"{BASE}/pit?session_key={session_key}"
    return _records_to_df(_request_json(url))


def fetch_position(session_key: int) -> pd.DataFrame:
    url = f"{BASE}/position?session_key={session_key}"
    return _records_to_df(_request_json(url))


def fetch_drivers(session_key: int) -> pd.DataFrame:
    url = f"{BASE}/drivers?session_key={session_key}"
    return _records_to_df(_request_json(url))


def fetch_weather(session_key: int) -> pd.DataFrame:
    url = f"{BASE}/weather?session_key={session_key}"
    return _records_to_df(_request_json(url))


def fetch_session_by_key(session_key: int) -> pd.DataFrame:
    url = f"{BASE}/sessions?session_key={session_key}"
    return _records_to_df(_request_json(url))


def fetch_qualifying_for_meeting(meeting_key: int, year: int) -> pd.DataFrame:
    url = f"{BASE}/sessions?session_type=Qualifying&year={year}&meeting_key={meeting_key}"
    df = _records_to_df(_request_json(url))
    if df.empty or "session_type" not in df.columns:
        return df
    # Exclude rows that are not the main "Qualifying" session (e.g. duplicate keys).
    return df[df["session_type"] == "Qualifying"].reset_index(drop=True)


def fetch_race_and_qual_sessions(years: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    race_parts: list[pd.DataFrame] = []
    qual_parts: list[pd.DataFrame] = []
    for y in years:
        race_parts.append(fetch_sessions("Race", y))
        qual_parts.append(fetch_sessions("Qualifying", y))
    races = pd.concat(race_parts, ignore_index=True) if race_parts else pd.DataFrame()
    quals = pd.concat(qual_parts, ignore_index=True) if qual_parts else pd.DataFrame()
    return races, quals
