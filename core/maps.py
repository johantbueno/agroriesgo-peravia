"""
Módulo de cartografía — AgroRisk Peravia v3.
Mapas coropléticos de República Dominicana con foco en zona Peravia.
Autor: Dr. Johan Tapia, PhD — Ministerio de Agricultura RD
"""
from __future__ import annotations
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# ── Provincias de RD con datos de mango ──────────────────────────────────
PROVINCIAS_DR = [
    # ── ZONA SUR (foco principal mango) ──
    {"id": "peravia",          "nombre": "Peravia",           "capital": "Baní",
     "lat": 18.28, "lon": -70.33, "mango_ha": 8500,  "region": "Sur", "foco": True},
    {"id": "azua",             "nombre": "Azua",              "capital": "Azua",
     "lat": 18.45, "lon": -70.74, "mango_ha": 5200,  "region": "Sur"},
    {"id": "san_cristobal",    "nombre": "San Cristóbal",     "capital": "San Cristóbal",
     "lat": 18.42, "lon": -70.11, "mango_ha": 3800,  "region": "Sur"},
    {"id": "sj_ocoa",          "nombre": "San José de Ocoa",  "capital": "Sabana Larga",
     "lat": 18.55, "lon": -70.50, "mango_ha": 2100,  "region": "Sur"},
    {"id": "barahona",         "nombre": "Barahona",          "capital": "Barahona",
     "lat": 18.21, "lon": -71.10, "mango_ha": 1800,  "region": "Sur"},
    {"id": "san_juan",         "nombre": "San Juan",          "capital": "San Juan de la Maguana",
     "lat": 18.81, "lon": -71.23, "mango_ha": 2800,  "region": "Suroeste"},
    {"id": "independencia",    "nombre": "Independencia",     "capital": "Jimaní",
     "lat": 18.49, "lon": -71.85, "mango_ha": 900,   "region": "Sur"},
    {"id": "pedernales",       "nombre": "Pedernales",        "capital": "Pedernales",
     "lat": 18.04, "lon": -71.74, "mango_ha": 450,   "region": "Sur"},
    {"id": "elias_pina",       "nombre": "Elías Piña",        "capital": "Comendador",
     "lat": 18.87, "lon": -71.69, "mango_ha": 800,   "region": "Suroeste"},
    # ── ZONA CIBAO / NORTE ──
    {"id": "santiago",         "nombre": "Santiago",          "capital": "Santiago de los Caballeros",
     "lat": 19.45, "lon": -70.69, "mango_ha": 6200,  "region": "Cibao"},
    {"id": "la_vega",          "nombre": "La Vega",           "capital": "La Vega",
     "lat": 19.22, "lon": -70.53, "mango_ha": 4100,  "region": "Cibao"},
    {"id": "monsenor_nouel",   "nombre": "Monseñor Nouel",    "capital": "Bonao",
     "lat": 18.92, "lon": -70.39, "mango_ha": 2900,  "region": "Cibao"},
    {"id": "espaillat",        "nombre": "Espaillat",         "capital": "Moca",
     "lat": 19.39, "lon": -70.52, "mango_ha": 1500,  "region": "Cibao"},
    {"id": "valverde",         "nombre": "Valverde",          "capital": "Mao",
     "lat": 19.55, "lon": -71.08, "mango_ha": 900,   "region": "Cibao"},
    {"id": "monte_cristi",     "nombre": "Monte Cristi",      "capital": "Monte Cristi",
     "lat": 19.86, "lon": -71.65, "mango_ha": 700,   "region": "Noroeste"},
    {"id": "s_rodriguez",      "nombre": "Santiago Rodríguez","capital": "Sabaneta",
     "lat": 19.49, "lon": -71.34, "mango_ha": 600,   "region": "Noroeste"},
    {"id": "dajabon",          "nombre": "Dajabón",           "capital": "Dajabón",
     "lat": 19.55, "lon": -71.71, "mango_ha": 400,   "region": "Noroeste"},
    {"id": "sanchez_ramirez",  "nombre": "Sánchez Ramírez",   "capital": "Cotuí",
     "lat": 19.05, "lon": -70.15, "mango_ha": 1800,  "region": "Cibao"},
    {"id": "puerto_plata",     "nombre": "Puerto Plata",      "capital": "Puerto Plata",
     "lat": 19.79, "lon": -70.69, "mango_ha": 1200,  "region": "Norte"},
    # ── ZONA ESTE ──
    {"id": "la_romana",        "nombre": "La Romana",         "capital": "La Romana",
     "lat": 18.43, "lon": -68.97, "mango_ha": 900,   "region": "Este"},
    {"id": "la_altagracia",    "nombre": "La Altagracia",     "capital": "Higüey",
     "lat": 18.62, "lon": -68.71, "mango_ha": 600,   "region": "Este"},
    {"id": "hato_mayor",       "nombre": "Hato Mayor",        "capital": "Hato Mayor",
     "lat": 18.76, "lon": -69.26, "mango_ha": 1400,  "region": "Este"},
    {"id": "el_seibo",         "nombre": "El Seibo",          "capital": "El Seibo",
     "lat": 18.77, "lon": -69.04, "mango_ha": 1100,  "region": "Este"},
    {"id": "monte_plata",      "nombre": "Monte Plata",       "capital": "Monte Plata",
     "lat": 18.81, "lon": -69.78, "mango_ha": 1500,  "region": "Este"},
    {"id": "samana",           "nombre": "Samaná",            "capital": "Samaná",
     "lat": 19.20, "lon": -69.34, "mango_ha": 800,   "region": "Nordeste"},
    {"id": "duarte",           "nombre": "Duarte",            "capital": "San Francisco de Macorís",
     "lat": 19.30, "lon": -70.25, "mango_ha": 1100,  "region": "Nordeste"},
    {"id": "maria_trinidad",   "nombre": "Mª Trinidad Sánchez","capital": "Nagua",
     "lat": 19.38, "lon": -69.84, "mango_ha": 500,   "region": "Nordeste"},
    # ── DISTRITO NACIONAL / SD ──
    {"id": "dn",               "nombre": "Distrito Nacional", "capital": "Santo Domingo",
     "lat": 18.48, "lon": -69.89, "mango_ha": 200,   "region": "Sur"},
    {"id": "santo_domingo",    "nombre": "Santo Domingo",     "capital": "Sto. Domingo Este",
     "lat": 18.50, "lon": -69.84, "mango_ha": 300,   "region": "Sur"},
]

# ── Zonas agrícolas de mango en Peravia ───────────────────────────────────
ZONAS_PERAVIA = [
    {"zona": "Baní Centro",       "lat": 18.2797, "lon": -70.3295, "ha": 1200,
     "tipo": "Valle costero",     "variedad": "Tommy Atkins"},
    {"zona": "Mata de Palma",     "lat": 18.300,  "lon": -70.280,  "ha": 950,
     "tipo": "Llanura interior",  "variedad": "Haden"},
    {"zona": "El Cedro",          "lat": 18.220,  "lon": -70.350,  "ha": 820,
     "tipo": "Ladera sur",        "variedad": "Kent"},
    {"zona": "Las Calderas",      "lat": 18.170,  "lon": -70.370,  "ha": 540,
     "tipo": "Zona costera",      "variedad": "Tommy Atkins"},
    {"zona": "Paya",              "lat": 18.350,  "lon": -70.250,  "ha": 1100,
     "tipo": "Zona montañosa",    "variedad": "Keitt"},
    {"zona": "Cambita Garabitos", "lat": 18.420,  "lon": -70.190,  "ha": 730,
     "tipo": "Transición S-N",   "variedad": "Haden"},
    {"zona": "Villa Fundación",   "lat": 18.330,  "lon": -70.410,  "ha": 860,
     "tipo": "Valle interior",    "variedad": "Kent"},
    {"zona": "San Gregorio",      "lat": 18.280,  "lon": -70.450,  "ha": 680,
     "tipo": "Piedemonte",        "variedad": "Tommy Atkins"},
    {"zona": "Baní Norte",        "lat": 18.380,  "lon": -70.320,  "ha": 590,
     "tipo": "Zona alta",         "variedad": "Keitt"},
    {"zona": "Penal-Boca Canasta","lat": 18.210,  "lon": -70.300,  "ha": 420,
     "tipo": "Litoral sur",       "variedad": "Haden"},
]

# ── Modificadores climáticos por región ──────────────────────────────────
_MOD_REGION = {
    "Sur":       {"mosca": 1.0,  "trips": 0.85, "antracnosis": 1.10, "oidio": 0.90},
    "Suroeste":  {"mosca": 0.90, "trips": 1.10, "antracnosis": 0.85, "oidio": 1.10},
    "Cibao":     {"mosca": 0.85, "trips": 0.90, "antracnosis": 0.95, "oidio": 1.00},
    "Norte":     {"mosca": 0.80, "trips": 0.85, "antracnosis": 1.05, "oidio": 0.95},
    "Noroeste":  {"mosca": 0.75, "trips": 1.15, "antracnosis": 0.80, "oidio": 1.15},
    "Este":      {"mosca": 0.90, "trips": 0.80, "antracnosis": 1.10, "oidio": 0.85},
    "Nordeste":  {"mosca": 0.85, "trips": 0.80, "antracnosis": 1.15, "oidio": 0.80},
}

_NIVEL_COLOR = {
    "Bajo":    "#4CAF50",
    "Medio":   "#FF9800",
    "Alto":    "#F44336",
    "Critico": "#7B1FA2",
}
_NIVEL_COLOR_A = {
    "Bajo":    "rgba(76,175,80,0.45)",
    "Medio":   "rgba(255,152,0,0.45)",
    "Alto":    "rgba(244,67,54,0.45)",
    "Critico": "rgba(123,31,162,0.45)",
}

def _score_to_nivel(s: float) -> str:
    if s < 25:  return "Bajo"
    if s < 50:  return "Medio"
    if s < 75:  return "Alto"
    return "Critico"


# ── Calcular riesgo para todas las provincias ────────────────────────────
def calcular_riesgo_nacional(resultados_peravia: dict) -> list[dict]:
    """
    Extrapola el riesgo de Peravia a las demás provincias usando
    modificadores climáticos regionales.
    """
    base = {a: resultados_peravia[a]["score"] for a in resultados_peravia}
    datos = []
    rng = np.random.default_rng(seed=99)

    for p in PROVINCIAS_DR:
        mod = _MOD_REGION.get(p["region"], {a: 1.0 for a in base})
        scores = {}
        riesgo_max = 0.0
        for amenaza, score_base in base.items():
            ruido = rng.normal(0, 3)
            s = float(np.clip(score_base * mod.get(amenaza, 1.0) + ruido, 0, 100))
            scores[amenaza] = round(s, 1)
            riesgo_max = max(riesgo_max, s)

        nivel = _score_to_nivel(riesgo_max)
        datos.append({**p, "scores": scores, "riesgo_max": round(riesgo_max, 1),
                      "nivel": nivel})
    return datos


# ── Calcular riesgo por zona de Peravia ──────────────────────────────────
def calcular_riesgo_zonas(resultados_peravia: dict) -> list[dict]:
    """Extrapola riesgo por microzona dentro de Peravia."""
    rng = np.random.default_rng(seed=77)
    zonas = []
    # Modificadores por tipo de zona
    _mod_tipo = {
        "Valle costero":    {"antracnosis": 1.15, "mosca": 1.10},
        "Llanura interior": {"mosca": 1.05},
        "Ladera sur":       {"trips": 0.95, "oidio": 1.05},
        "Zona costera":     {"antracnosis": 1.20, "mosca": 1.15},
        "Zona montañosa":   {"oidio": 1.10, "trips": 1.05, "antracnosis": 0.90},
        "Transición S-N":   {},
        "Valle interior":   {"mosca": 1.05, "antracnosis": 1.05},
        "Piedemonte":       {"oidio": 1.05, "trips": 1.00},
        "Zona alta":        {"oidio": 1.15, "antracnosis": 0.88, "trips": 1.08},
        "Litoral sur":      {"antracnosis": 1.25, "mosca": 1.20},
    }
    for z in ZONAS_PERAVIA:
        mod = _mod_tipo.get(z["tipo"], {})
        scores = {}
        riesgo_max = 0.0
        for amenaza, d in resultados_peravia.items():
            s = float(np.clip(d["score"] * mod.get(amenaza, 1.0) + rng.normal(0, 2.5), 0, 100))
            scores[amenaza] = round(s, 1)
            riesgo_max = max(riesgo_max, s)
        nivel = _score_to_nivel(riesgo_max)
        zonas.append({**z, "scores": scores, "riesgo_max": round(riesgo_max, 1),
                      "nivel": nivel})
    return zonas


# ── Figuras de mapa ──────────────────────────────────────────────────────

def mapa_nacional_dr(datos_provincias: list[dict], amenaza: str = "riesgo_max") -> go.Figure:
    """
    Mapa burbuja de República Dominicana con riesgo por provincia.
    """
    lats     = [p["lat"] for p in datos_provincias]
    lons     = [p["lon"] for p in datos_provincias]
    nombres  = [p["nombre"] for p in datos_provincias]
    capitales= [p["capital"] for p in datos_provincias]
    niveles  = [p["nivel"] for p in datos_provincias]
    riesgos  = [p["riesgo_max"] for p in datos_provincias]
    mango_ha = [p["mango_ha"] for p in datos_provincias]
    es_foco  = [p.get("foco", False) for p in datos_provincias]
    colores  = [_NIVEL_COLOR[n] for n in niveles]
    sizes    = [max(18, int(r * 0.55)) for r in riesgos]

    hover_texts = []
    for p in datos_provincias:
        sc = p["scores"]
        t = (
            f"<b>{p['nombre']}</b><br>"
            f"Capital: {p['capital']}<br>"
            f"Area mango: {p['mango_ha']:,} ha<br>"
            f"Riesgo global: <b>{p['riesgo_max']:.1f}/100</b> ({p['nivel']})<br>"
            f"─────────────────<br>"
            f"Mosca: {sc.get('mosca',0):.1f} &nbsp; Trips: {sc.get('trips',0):.1f}<br>"
            f"Antracnosis: {sc.get('antracnosis',0):.1f} &nbsp; Oídio: {sc.get('oidio',0):.1f}"
        )
        hover_texts.append(t)

    fig = go.Figure()

    # Capa de burbujas
    fig.add_trace(go.Scattermapbox(
        lat=lats, lon=lons,
        mode="markers",
        marker=dict(
            size=sizes,
            color=riesgos,
            colorscale=[
                [0.00, "#4CAF50"],
                [0.25, "#8BC34A"],
                [0.50, "#FF9800"],
                [0.75, "#F44336"],
                [1.00, "#7B1FA2"],
            ],
            cmin=0, cmax=100,
            opacity=0.82,
            colorbar=dict(
                title="Indice<br>Riesgo",
                tickvals=[0, 25, 50, 75, 100],
                ticktext=["Bajo", "Medio", "Alto", "Critico", "Max"],
                thickness=14, len=0.7,
                bgcolor="rgba(255,255,255,0.85)",
            ),
        ),
        text=hover_texts,
        hoverinfo="text",
        name="Provincias",
    ))

    # Marcador especial para Peravia
    foco_idx = next((i for i, p in enumerate(datos_provincias) if p.get("foco")), None)
    if foco_idx is not None:
        p = datos_provincias[foco_idx]
        fig.add_trace(go.Scattermapbox(
            lat=[p["lat"]], lon=[p["lon"]],
            mode="markers+text",
            marker=dict(size=22, color="#F9A825", symbol="star"),
            text=["PERAVIA"],
            textposition="top center",
            textfont=dict(size=12, color="#F9A825", family="Arial Black"),
            hoverinfo="skip",
            name="Zona Peravia",
        ))

    # Etiquetas de capitales para principales
    principales = [p for p in datos_provincias if p["mango_ha"] >= 3000]
    fig.add_trace(go.Scattermapbox(
        lat=[p["lat"] for p in principales],
        lon=[p["lon"] for p in principales],
        mode="text",
        text=[p["nombre"] for p in principales],
        textfont=dict(size=9, color="#1A1A1A"),
        hoverinfo="skip",
        name="",
    ))

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=18.7, lon=-70.15),
            zoom=6.8,
        ),
        height=520,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def mapa_peravia_detalle(zonas: list[dict]) -> go.Figure:
    """
    Mapa detallado de zonas agrícolas de mango en Peravia.
    """
    lats     = [z["lat"] for z in zonas]
    lons     = [z["lon"] for z in zonas]
    niveles  = [z["nivel"] for z in zonas]
    riesgos  = [z["riesgo_max"] for z in zonas]
    sizes    = [max(20, int(r * 0.65)) for r in riesgos]

    hover_texts = []
    for z in zonas:
        sc = z["scores"]
        t = (
            f"<b>{z['zona']}</b><br>"
            f"Tipo: {z['tipo']}<br>"
            f"Variedad: {z['variedad']}<br>"
            f"Area: {z['ha']:,} ha<br>"
            f"Riesgo global: <b>{z['riesgo_max']:.1f}/100</b> ({z['nivel']})<br>"
            f"──────────────<br>"
            f"Mosca: {sc.get('mosca',0):.1f}<br>"
            f"Trips: {sc.get('trips',0):.1f}<br>"
            f"Antracnosis: {sc.get('antracnosis',0):.1f}<br>"
            f"Oídio: {sc.get('oidio',0):.1f}"
        )
        hover_texts.append(t)

    fig = go.Figure()

    fig.add_trace(go.Scattermapbox(
        lat=lats, lon=lons,
        mode="markers+text",
        marker=dict(
            size=sizes,
            color=riesgos,
            colorscale=[
                [0.0,  "#4CAF50"],
                [0.25, "#8BC34A"],
                [0.5,  "#FF9800"],
                [0.75, "#F44336"],
                [1.0,  "#7B1FA2"],
            ],
            cmin=0, cmax=100,
            opacity=0.85,
            colorbar=dict(
                title="Riesgo",
                tickvals=[0, 25, 50, 75, 100],
                ticktext=["Bajo", "Medio", "Alto", "Critico", "Max"],
                thickness=12, len=0.6,
                bgcolor="rgba(255,255,255,0.85)",
            ),
        ),
        text=[z["zona"] for z in zonas],
        textposition="top right",
        textfont=dict(size=10, color="#1B5E20", family="Arial"),
        hovertext=hover_texts,
        hoverinfo="text",
        name="Zonas mango",
    ))

    # Punto central de Baní
    fig.add_trace(go.Scattermapbox(
        lat=[18.2797], lon=[-70.3295],
        mode="markers+text",
        marker=dict(size=16, color="#1B5E20", symbol="circle"),
        text=["Baní"],
        textposition="bottom right",
        textfont=dict(size=11, color="#1B5E20", family="Arial Black"),
        hoverinfo="skip",
        name="Capital",
    ))

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=18.29, lon=-70.33),
            zoom=10.5,
        ),
        height=500,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def mapa_densidad_riesgo(zonas: list[dict], amenaza: str = "mosca") -> go.Figure:
    """Mapa de densidad (heatmap) de riesgo para una amenaza específica."""
    fig = go.Figure()
    fig.add_trace(go.Densitymapbox(
        lat=[z["lat"] for z in zonas],
        lon=[z["lon"] for z in zonas],
        z=[z["scores"].get(amenaza, 0) for z in zonas],
        radius=40,
        colorscale=[
            [0.0,  "rgba(76,175,80,0)"],
            [0.25, "rgba(139,195,74,0.4)"],
            [0.50, "rgba(255,152,0,0.6)"],
            [0.75, "rgba(244,67,54,0.75)"],
            [1.0,  "rgba(123,31,162,0.9)"],
        ],
        colorbar=dict(title="Riesgo", thickness=12),
        hovertemplate="Riesgo: %{z:.1f}<extra></extra>",
        name=amenaza,
    ))
    fig.update_layout(
        mapbox=dict(style="open-street-map",
                    center=dict(lat=18.29, lon=-70.33), zoom=10),
        height=450,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
