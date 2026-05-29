"""
Integración con Open-Meteo para Baní, Peravia (lat=18.28, lon=-70.33).
Cachea la respuesta 1 hora en SQLite para evitar sobrecarga de la API.
"""
from __future__ import annotations

import sqlite3
import json
import time
from datetime import date, datetime
from pathlib import Path

import requests

LAT = 18.28
LON = -70.33
CACHE_DB = Path(__file__).parent.parent / "data" / "cache.db"
CACHE_TTL = 3600  # 1 hora

# Valores de fallback para cuando la API no está disponible
FALLBACK = {
    "temp_max": 30.5,
    "temp_min": 24.0,
    "temp_media": 27.2,
    "humedad": 72.0,
    "precipitacion": 3.2,
    "source": "fallback",
}


def _init_cache() -> sqlite3.Connection:
    CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CACHE_DB))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS api_cache "
        "(key TEXT PRIMARY KEY, data TEXT, ts REAL)"
    )
    conn.commit()
    return conn


def _get_cached(key: str) -> dict | None:
    conn = _init_cache()
    row = conn.execute(
        "SELECT data, ts FROM api_cache WHERE key=?", (key,)
    ).fetchone()
    conn.close()
    if row and (time.time() - row[1]) < CACHE_TTL:
        return json.loads(row[0])
    return None


def _set_cache(key: str, data: dict) -> None:
    conn = _init_cache()
    conn.execute(
        "INSERT OR REPLACE INTO api_cache (key, data, ts) VALUES (?,?,?)",
        (key, json.dumps(data), time.time()),
    )
    conn.commit()
    conn.close()


def fetch_today() -> dict:
    """
    Devuelve datos climáticos del día actual para Baní.
    Claves: temp_max, temp_min, temp_media, humedad, precipitacion, source
    """
    today = date.today().isoformat()
    cache_key = f"forecast_{today}"

    cached = _get_cached(cache_key)
    if cached:
        cached["source"] = "cache"
        return cached

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
        ],
        "hourly": ["relative_humidity_2m"],
        "timezone": "America/Santo_Domingo",
        "forecast_days": 1,
    }

    try:
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        raw = resp.json()

        temp_max = raw["daily"]["temperature_2m_max"][0] or FALLBACK["temp_max"]
        temp_min = raw["daily"]["temperature_2m_min"][0] or FALLBACK["temp_min"]
        lluvia   = raw["daily"]["precipitation_sum"][0] or 0.0
        hum_vals = [v for v in raw["hourly"]["relative_humidity_2m"] if v is not None]
        humedad  = round(sum(hum_vals) / len(hum_vals), 1) if hum_vals else FALLBACK["humedad"]

        data = {
            "temp_max": round(temp_max, 1),
            "temp_min": round(temp_min, 1),
            "temp_media": round((temp_max + temp_min) / 2, 1),
            "humedad": humedad,
            "precipitacion": round(lluvia, 1),
            "source": "api",
        }
        _set_cache(cache_key, data)
        return data

    except Exception:
        return dict(FALLBACK)


def fetch_forecast_week() -> list[dict]:
    """
    Devuelve pronóstico de 7 días para Baní.
    Cada elemento: fecha, temp_max, temp_min, precipitacion
    """
    cache_key = f"week_{date.today().isoformat()}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
        ],
        "timezone": "America/Santo_Domingo",
        "forecast_days": 7,
    }

    try:
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        raw = resp.json()

        result = []
        for i, d in enumerate(raw["daily"]["time"]):
            result.append({
                "fecha": d,
                "temp_max": raw["daily"]["temperature_2m_max"][i],
                "temp_min": raw["daily"]["temperature_2m_min"][i],
                "precipitacion": raw["daily"]["precipitation_sum"][i] or 0.0,
            })
        _set_cache(cache_key, result)
        return result
    except Exception:
        return []
