"""
Historial de predicciones y alertas — SQLite.
"""
from __future__ import annotations

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "historial.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    con = _conn()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS predicciones (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT    NOT NULL,
            temperatura REAL,
            humedad     REAL,
            precipitacion REAL,
            dias_sin_lluvia INTEGER,
            fenologia   INTEGER,
            mes         INTEGER,
            resultados  TEXT,
            fuente      TEXT DEFAULT 'manual'
        );
        CREATE TABLE IF NOT EXISTS alertas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT    NOT NULL,
            amenaza     TEXT    NOT NULL,
            nivel       TEXT    NOT NULL,
            score       REAL,
            vista       INTEGER DEFAULT 0
        );
    """)
    con.commit()
    con.close()


def guardar_prediccion(clima: dict, resultados: dict, fuente: str = "manual") -> int:
    init_db()
    con = _conn()
    cur = con.execute(
        """INSERT INTO predicciones
           (timestamp, temperatura, humedad, precipitacion, dias_sin_lluvia,
            fenologia, mes, resultados, fuente)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            datetime.now().isoformat(timespec="seconds"),
            clima.get("temperatura"),
            clima.get("humedad"),
            clima.get("precipitacion"),
            clima.get("dias_sin_lluvia"),
            clima.get("fenologia"),
            clima.get("mes"),
            json.dumps(resultados, ensure_ascii=False),
            fuente,
        ),
    )
    row_id = cur.lastrowid

    # Registrar alertas para niveles Alto / Critico
    for amenaza, data in resultados.items():
        if data["nivel"] in ("Alto", "Critico"):
            con.execute(
                "INSERT INTO alertas (timestamp, amenaza, nivel, score) VALUES (?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), amenaza,
                 data["nivel"], data["score"]),
            )
    con.commit()
    con.close()
    return row_id


def obtener_historial(limit: int = 200) -> list[dict]:
    init_db()
    con = _conn()
    rows = con.execute(
        "SELECT * FROM predicciones ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    con.close()
    result = []
    for r in rows:
        d = dict(r)
        d["resultados"] = json.loads(d["resultados"])
        result.append(d)
    return result


def obtener_alertas_activas(limit: int = 20) -> list[dict]:
    init_db()
    con = _conn()
    rows = con.execute(
        "SELECT * FROM alertas WHERE vista=0 ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def marcar_alertas_vistas() -> None:
    init_db()
    con = _conn()
    con.execute("UPDATE alertas SET vista=1 WHERE vista=0")
    con.commit()
    con.close()
