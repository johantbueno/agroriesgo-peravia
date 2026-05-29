"""
Generador de datos históricos sintéticos para Peravia (Baní, RD).
Patrones climáticos basados en registros de ONAMET zona sur.
"""
import numpy as np
import pandas as pd
from datetime import date

RNG = np.random.default_rng(seed=42)

# Etapas fenológicas del mango codificadas
FENOLOGIA_MAP = {
    "Reposo vegetativo": 0,
    "Brotacion":         1,
    "Floracion":         2,
    "Fruto joven":       3,
    "Maduracion":        4,
}
FENOLOGIA_LABELS = list(FENOLOGIA_MAP.keys())

# Calendario fenológico típico para Baní (mes → etapa dominante)
_MES_FENOLOGIA = {
    1: 2, 2: 2, 3: 3, 4: 3,   # ene-abr: floración / fruto joven
    5: 3, 6: 4, 7: 4, 8: 4,   # may-ago: fruto joven / maduración
    9: 4, 10: 0, 11: 0, 12: 1, # sep-oct: maduración / reposo / brotación
}


def _fenologia_encoded(mes: int) -> int:
    return _MES_FENOLOGIA.get(mes, 0)


def _clima_diario(mes: int) -> tuple[float, float, float]:
    """Devuelve (temp_media, humedad_media, lluvia_media) según estación."""
    temporada_lluviosa = mes in range(5, 12)  # may-nov
    if temporada_lluviosa:
        temp   = RNG.normal(28.0, 1.5)
        hum    = RNG.normal(78.0, 5.0)
        lluvia = max(0.0, RNG.exponential(12.0))
    else:
        temp   = RNG.normal(30.0, 1.8)
        hum    = RNG.normal(60.0, 5.0)
        lluvia = max(0.0, RNG.exponential(2.5))
    return float(np.clip(temp, 20, 38)), float(np.clip(hum, 35, 98)), round(lluvia, 1)


def generate_historical(start: str = "2022-01-01", end: str = "2024-12-31") -> pd.DataFrame:
    """
    Genera DataFrame diario con features climáticas y scores de riesgo sintéticos.
    """
    idx = pd.date_range(start=start, end=end, freq="D")
    rows = []
    dias_sin_lluvia = 0

    for dt in idx:
        mes = dt.month
        temp, hum, lluvia = _clima_diario(mes)
        if lluvia < 0.5:
            dias_sin_lluvia += 1
        else:
            dias_sin_lluvia = 0

        feno = _fenologia_encoded(mes)
        interaccion = (temp * hum) / 1000.0

        # ── Riesgo Mosca de las Frutas ──────────────────────────────
        r_mosca = 0.0
        if temp > 25:
            r_mosca += (temp - 25) * 3.5
        if hum > 65:
            r_mosca += (hum - 65) * 0.8
        if feno in (3, 4):   # fruto joven / maduración
            r_mosca *= 1.5
        r_mosca += RNG.normal(0, 4)
        r_mosca = float(np.clip(r_mosca, 0, 100))

        # ── Riesgo Trips ────────────────────────────────────────────
        r_trips = 0.0
        if temp > 27:
            r_trips += (temp - 27) * 4.0
        if hum < 65:
            r_trips += (65 - hum) * 0.7
        if dias_sin_lluvia > 5:
            r_trips += dias_sin_lluvia * 1.2
        if feno == 2:        # floración
            r_trips *= 1.4
        r_trips += RNG.normal(0, 4)
        r_trips = float(np.clip(r_trips, 0, 100))

        # ── Riesgo Antracnosis ──────────────────────────────────────
        r_antracnosis = 0.0
        if hum > 75:
            r_antracnosis += (hum - 75) * 2.5
        if lluvia > 5:
            r_antracnosis += lluvia * 1.2
        if 24 <= temp <= 32:
            r_antracnosis += 15
        if feno == 4:        # maduración
            r_antracnosis *= 1.3
        r_antracnosis += RNG.normal(0, 5)
        r_antracnosis = float(np.clip(r_antracnosis, 0, 100))

        # ── Riesgo Oídio ────────────────────────────────────────────
        r_oidio = 0.0
        if 22 <= temp <= 30:
            r_oidio += 20
        if 40 <= hum <= 70:
            r_oidio += (70 - hum) * 0.6
        if dias_sin_lluvia > 3:
            r_oidio += dias_sin_lluvia * 1.5
        if feno == 2:        # floración
            r_oidio *= 1.4
        r_oidio += RNG.normal(0, 4)
        r_oidio = float(np.clip(r_oidio, 0, 100))

        rows.append({
            "fecha": dt,
            "mes": mes,
            "temperatura": round(temp, 1),
            "humedad": round(hum, 1),
            "precipitacion": round(lluvia, 1),
            "dias_sin_lluvia": dias_sin_lluvia,
            "fenologia": feno,
            "interaccion_temp_hum": round(interaccion, 3),
            "riesgo_mosca": round(r_mosca, 1),
            "riesgo_trips": round(r_trips, 1),
            "riesgo_antracnosis": round(r_antracnosis, 1),
            "riesgo_oidio": round(r_oidio, 1),
        })

    return pd.DataFrame(rows)
