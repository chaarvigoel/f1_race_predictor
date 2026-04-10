"""OpenF1 API client. All requests are sequential with rate limiting."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd
import requests

BASE = "https://api.openf1.org/v1"
REQUEST_GAP_S = 0.4


def _request_json(url: str) -> list[dict[str, Any]]:
    time.sleep(REQUEST_GAP_S)
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        return []
    except Exception:
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
    return _records_to_df(_request_json(url))


def fetch_race_and_qual_sessions(years: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    race_parts: list[pd.DataFrame] = []
    qual_parts: list[pd.DataFrame] = []
    for y in years:
        race_parts.append(fetch_sessions("Race", y))
        qual_parts.append(fetch_sessions("Qualifying", y))
    races = pd.concat(race_parts, ignore_index=True) if race_parts else pd.DataFrame()
    quals = pd.concat(qual_parts, ignore_index=True) if qual_parts else pd.DataFrame()
    return races, quals
