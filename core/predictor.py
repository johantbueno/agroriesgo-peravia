"""
Motor de predicción fitosanitaria — Random Forest por amenaza.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler

from core.data_generator import generate_historical, FENOLOGIA_MAP, FENOLOGIA_LABELS

AMENAZAS = ["mosca", "trips", "antracnosis", "oidio"]

NIVELES = [
    (0,  25,  "Bajo",    "#4CAF50"),
    (25, 50,  "Medio",   "#FF9800"),
    (50, 75,  "Alto",    "#F44336"),
    (75, 101, "Critico", "#7B1FA2"),
]

RECOMENDACIONES: dict[str, dict[str, str]] = {
    "mosca": {
        "Bajo":    "Monitoreo preventivo semanal con trampas McPhail.",
        "Medio":   "Incrementar frecuencia de monitoreo a dos veces por semana. Recolectar frutos caidos.",
        "Alto":    "Colocar trampas McPhail con proteina hidrolizada. Recolectar frutos caidos diariamente. Considerar control biologico con Diachasmimorpha.",
        "Critico": "Aplicacion de proteina hidrolizada con insecticida organico (Spinosad) en perimetro. Recoleccion diaria obligatoria. Notificar a DIFA.",
    },
    "trips": {
        "Bajo":    "Inspeccion visual en flores durante horas frescas.",
        "Medio":   "Monitoreo con trampas azules adhesivas en panoja.",
        "Alto":    "Inspeccionar flores en horas tempranas. Considerar Spinosad si supera umbral economico (10 trips/flor).",
        "Critico": "Aplicacion inmediata de Spinosad o Abamectina. Repetir a los 7 dias si persiste infestacion.",
    },
    "antracnosis": {
        "Bajo":    "Mantener podas de ventilacion. Evitar exceso de riego.",
        "Medio":   "Aplicar fungicida cuprico preventivo. Revisar densidad del dosel.",
        "Alto":    "Aplicar fungicida cuprico preventivo. Evitar riego por aspersion. Destruir material infectado.",
        "Critico": "Aplicacion urgente de Mancozeb o Azoxistrobina. Eliminar frutos y hojas infectadas. Desinfectar herramientas.",
    },
    "oidio": {
        "Bajo":    "Monitoreo visual en brotaciones jovenes.",
        "Medio":   "Aplicar azufre mojable preventivo en paniculas.",
        "Alto":    "Aplicar azufre mojable en panicula floral. Reducir densidad de copa.",
        "Critico": "Aplicacion de Miclobutanil o Trifloxistrobina. Podas sanitarias urgentes. Evitar fertilizacion nitrogenada excesiva.",
    },
}

FEATURES = [
    "temperatura", "humedad", "precipitacion", "dias_sin_lluvia",
    "fenologia", "mes", "interaccion_temp_hum",
]


def _nivel(score: float) -> tuple[str, str]:
    for lo, hi, nombre, color in NIVELES:
        if lo <= score < hi:
            return nombre, color
    return "Critico", "#7B1FA2"


class AgroRiskPredictor:
    def __init__(self) -> None:
        self._models: dict[str, RandomForestRegressor] = {}
        self._scaler = MinMaxScaler()
        self._trained = False
        self._feature_importances: dict[str, pd.Series] = {}

    # ── Entrenamiento ──────────────────────────────────────────────
    def train(self, df: pd.DataFrame | None = None) -> None:
        if df is None:
            df = generate_historical()

        X = df[FEATURES].values
        self._scaler.fit(X)
        X_scaled = self._scaler.transform(X)

        for amenaza in AMENAZAS:
            y = df[f"riesgo_{amenaza}"].values
            rf = RandomForestRegressor(
                n_estimators=150,
                max_depth=8,
                min_samples_split=4,
                random_state=42,
                n_jobs=-1,
            )
            rf.fit(X_scaled, y)
            self._models[amenaza] = rf
            self._feature_importances[amenaza] = pd.Series(
                rf.feature_importances_, index=FEATURES
            ).sort_values(ascending=False)

        self._trained = True

    # ── Prediccion individual ──────────────────────────────────────
    def predict(self, temp: float, hum: float, lluvia: float,
                dias_sin_lluvia: int, fenologia: int, mes: int) -> dict:
        if not self._trained:
            self.train()

        interaccion = (temp * hum) / 1000.0
        row = np.array([[temp, hum, lluvia, dias_sin_lluvia,
                         fenologia, mes, interaccion]], dtype=float)
        row_scaled = self._scaler.transform(row)

        result: dict[str, dict] = {}
        for amenaza in AMENAZAS:
            score = float(np.clip(self._models[amenaza].predict(row_scaled)[0], 0, 100))
            nivel, color = _nivel(score)
            prob_7d = min(100.0, score * 1.15)
            result[amenaza] = {
                "score": round(score, 1),
                "nivel": nivel,
                "color": color,
                "prob_7d": round(prob_7d, 1),
                "recomendacion": RECOMENDACIONES[amenaza][nivel],
            }
        return result

    # ── Prediccion batch ───────────────────────────────────────────
    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._trained:
            self.train()

        df = df.copy()
        if "interaccion_temp_hum" not in df.columns:
            df["interaccion_temp_hum"] = (df["temperatura"] * df["humedad"]) / 1000.0

        X = df[FEATURES].values
        X_scaled = self._scaler.transform(X)

        for amenaza in AMENAZAS:
            preds = self._models[amenaza].predict(X_scaled)
            df[f"pred_{amenaza}"] = np.clip(preds, 0, 100).round(1)

        return df

    # ── Importancia de features ────────────────────────────────────
    def get_feature_importance(self, amenaza: str) -> pd.Series:
        if not self._trained:
            self.train()
        return self._feature_importances.get(amenaza, pd.Series())

    # ── Helper nivel ──────────────────────────────────────────────
    @staticmethod
    def nivel_from_score(score: float) -> tuple[str, str]:
        return _nivel(score)
