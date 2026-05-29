"""
Simulador de Condiciones v2 — AgroRisk Peravia.
Gauges animados + análisis de factor dominante + asistente inline.
"""
from __future__ import annotations

from datetime import date

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from core.predictor import AgroRiskPredictor, AMENAZAS
from core.data_generator import FENOLOGIA_LABELS, FENOLOGIA_MAP
from core.database import guardar_prediccion
from core.asistente_ia import AgroAsistente, _nombre

AMENAZA_LABEL = {
    "mosca":        "Mosca de las Frutas",
    "trips":        "Trips",
    "antracnosis":  "Antracnosis",
    "oidio":        "Oidio",
}
MESES = [
    "Enero","Febrero","Marzo","Abril","Mayo","Junio",
    "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre",
]


def render(predictor: AgroRiskPredictor) -> None:
    st.markdown("## Simulador de Condiciones Climaticas")
    st.markdown(
        "Ajuste los parametros para evaluar el riesgo fitosanitario "
        "en cualquier escenario hipotetico. Los resultados se actualizan en tiempo real."
    )
    st.markdown("---")

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown("#### Parametros de Entrada")

        temperatura = st.slider("Temperatura media (°C)", 18.0, 40.0, 28.0, 0.5)
        humedad     = st.slider("Humedad relativa (%)", 30, 100, 70, 1)
        precipitacion    = st.slider("Precipitacion diaria (mm)", 0.0, 80.0, 5.0, 0.5)
        dias_sin_lluvia  = st.slider("Dias consecutivos sin lluvia", 0, 30, 3, 1)

        st.markdown("#### Fenologia y Periodo")
        feno_label = st.selectbox("Etapa fenologica", FENOLOGIA_LABELS, index=2)
        mes_label  = st.selectbox("Mes", MESES, index=date.today().month - 1)

        # Indicadores de condicion
        st.markdown("#### Condicion Actual")
        _semaforo_clima(temperatura, humedad, precipitacion, dias_sin_lluvia)

    feno_val = FENOLOGIA_MAP[feno_label]
    mes_val  = MESES.index(mes_label) + 1

    resultado = predictor.predict(
        temp=temperatura, hum=humedad, lluvia=precipitacion,
        dias_sin_lluvia=dias_sin_lluvia, fenologia=feno_val, mes=mes_val,
    )

    with col_right:
        st.markdown("#### Indices de Riesgo (tiempo real)")
        _render_gauges_2x2(resultado)

    st.markdown("---")

    # ── Radar de comparacion ───────────────────────────────────────
    st.markdown("### Perfil de Riesgo del Escenario")
    _render_barras_h(resultado)

    st.markdown("---")

    # ── Asistente inline ───────────────────────────────────────────
    st.markdown("### Analisis del Asistente IA")
    asistente = AgroAsistente()
    analisis  = asistente.analizar(
        resultado,
        {"temp_media": temperatura, "humedad": humedad,
         "precipitacion": precipitacion, "source": "simulador"},
        feno_val, mes_val,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        bg_map = {
            "Bajo": "#E8F5E9", "Moderado": "#FFF8E1",
            "Elevado": "#FBE9E7", "Critico": "#F3E5F5",
        }
        fg_map = {
            "Bajo": "#2E7D32", "Moderado": "#F57F17",
            "Elevado": "#BF360C", "Critico": "#4A148C",
        }
        ng = analisis["nivel_alerta_global"]
        st.markdown(
            f'<div style="background:{bg_map[ng]};border-radius:10px;padding:16px;">'
            f'<div style="font-size:0.8rem;font-weight:700;color:{fg_map[ng]};">'
            f'NIVEL GLOBAL: {ng.upper()}</div>'
            f'<div style="font-size:0.88rem;color:#444;margin-top:8px;line-height:1.5;">'
            f'{analisis["resumen"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_b:
        st.markdown("**Plan de accion para este escenario:**")
        for paso in analisis["plan_accion"]:
            tag = paso.split("]")[0].replace("[", "")
            texto = paso.split("] ", 1)[-1] if "] " in paso else paso
            c_map = {"URGENTE": "#F44336", "PREVENTIVO": "#FF9800", "MONITOREO": "#4CAF50"}
            c = c_map.get(tag, "#999")
            st.markdown(
                f'<div style="border-left:3px solid {c};padding:6px 10px;'
                f'margin-bottom:6px;font-size:0.85rem;">'
                f'<strong style="color:{c};">{tag}</strong><br>{texto}</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Guardar ────────────────────────────────────────────────────
    col_g, _ = st.columns([2, 5])
    with col_g:
        if st.button("Guardar simulacion en historial"):
            guardar_prediccion(
                clima={
                    "temperatura": temperatura, "humedad": humedad,
                    "precipitacion": precipitacion, "dias_sin_lluvia": dias_sin_lluvia,
                    "fenologia": feno_val, "mes": mes_val,
                },
                resultados=resultado, fuente="simulador",
            )
            st.success("Simulacion guardada.")


# ── Helpers visuales ───────────────────────────────────────────────────────

def _semaforo_clima(temp, hum, lluvia, secos):
    items = []
    # Temperatura
    if temp > 32:
        items.append(("Temperatura muy alta", "#F44336", f"{temp}°C — favorece mosca y trips"))
    elif temp > 27:
        items.append(("Temperatura alta", "#FF9800", f"{temp}°C — riesgo moderado mosca"))
    else:
        items.append(("Temperatura normal", "#4CAF50", f"{temp}°C — condicion favorable"))
    # Humedad
    if hum > 80:
        items.append(("Humedad critica", "#F44336", f"{hum}% — riesgo alto de antracnosis"))
    elif hum < 55:
        items.append(("Humedad muy baja", "#FF9800", f"{hum}% — favorece trips y oidio"))
    else:
        items.append(("Humedad normal", "#4CAF50", f"{hum}% — condicion neutra"))
    # Dias secos
    if secos > 10:
        items.append(("Sequia prolongada", "#F44336", f"{secos} dias — oidio critico"))
    elif secos > 5:
        items.append(("Periodo seco", "#FF9800", f"{secos} dias — vigilar trips"))
    else:
        items.append(("Sin sequia", "#4CAF50", f"{secos} dias sin lluvia"))

    for titulo, color, detalle in items:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'background:white;border-radius:8px;padding:8px 12px;'
            f'margin-bottom:6px;border-left:4px solid {color};">'
            f'<div style="width:10px;height:10px;border-radius:50%;'
            f'background:{color};flex-shrink:0;"></div>'
            f'<div><div style="font-size:0.8rem;font-weight:600;">{titulo}</div>'
            f'<div style="font-size:0.75rem;color:#666;">{detalle}</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_gauges_2x2(resultado: dict) -> None:
    amenazas = list(AMENAZA_LABEL.keys())
    fig = make_subplots(
        rows=2, cols=2,
        specs=[[{"type":"indicator"}, {"type":"indicator"}],
               [{"type":"indicator"}, {"type":"indicator"}]],
        vertical_spacing=0.15, horizontal_spacing=0.08,
    )
    positions = [(1,1),(1,2),(2,1),(2,2)]
    for i, amenaza in enumerate(amenazas):
        d = resultado[amenaza]
        r, c = positions[i]
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=d["score"],
            title={"text": AMENAZA_LABEL[amenaza], "font": {"size": 11}},
            number={"font": {"size": 20, "color": d["color"]}},
            gauge={
                "axis": {"range":[0,100], "tickfont":{"size":8}},
                "bar": {"color": d["color"], "thickness":0.3},
                "steps": [
                    {"range":[0,25],  "color":"#E8F5E9"},
                    {"range":[25,50], "color":"#FFF8E1"},
                    {"range":[50,75], "color":"#FFEBEE"},
                    {"range":[75,100],"color":"#F3E5F5"},
                ],
                "threshold": {
                    "line":{"color":d["color"],"width":3},
                    "thickness":0.8, "value":d["score"],
                },
            },
        ), row=r, col=c)

    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_barras_h(resultado: dict) -> None:
    amenazas = list(AMENAZA_LABEL.values())
    scores   = [resultado[a]["score"] for a in AMENAZA_LABEL]
    colors   = [resultado[a]["color"] for a in AMENAZA_LABEL]

    fig = go.Figure(go.Bar(
        y=amenazas, x=scores,
        orientation="h",
        marker_color=colors,
        text=[f"{s:.1f}" for s in scores],
        textposition="outside",
    ))
    # Zonas de referencia
    for x0, x1, color, label in [
        (0, 25, "rgba(76,175,80,0.08)", "Bajo"),
        (25, 50, "rgba(255,152,0,0.08)", "Medio"),
        (50, 75, "rgba(244,67,54,0.08)", "Alto"),
        (75, 100, "rgba(123,31,162,0.08)", "Critico"),
    ]:
        fig.add_vrect(x0=x0, x1=x1, fillcolor=color, line_width=0,
                      annotation_text=label,
                      annotation_position="top",
                      annotation=dict(font_size=9, font_color="#aaa"))

    fig.update_layout(
        xaxis=dict(range=[0,115], title="Indice de riesgo (0–100)"),
        yaxis=dict(title=""),
        height=280,
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor="#F9FBF9",
        title=dict(
            text="Zona: Peravia — Bani  |  Modelo AgroRisk v1.0",
            font={"size":10,"color":"#888"}, x=0.5,
        ),
    )
    st.plotly_chart(fig, use_container_width=True)
