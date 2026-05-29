"""
Dashboard principal — AgroRisk Peravia v2.
"""
from __future__ import annotations

from datetime import date

import plotly.graph_objects as go
import streamlit as st

from core.climate_api import fetch_today
from core.database import guardar_prediccion, obtener_alertas_activas, marcar_alertas_vistas
from core.data_generator import FENOLOGIA_LABELS, FENOLOGIA_MAP

AMENAZA_LABEL = {
    "mosca":        "Mosca de las Frutas",
    "trips":        "Trips",
    "antracnosis":  "Antracnosis",
    "oidio":        "Oidio",
}
AMENAZA_ICON = {
    "mosca": "🪰", "trips": "🦟", "antracnosis": "🍂", "oidio": "🌫",
}

_NIVEL_CSS = {"bajo": "#4CAF50", "medio": "#FF9800", "alto": "#F44336", "critico": "#7B1FA2"}


def render(predictor) -> None:
    st.markdown("# Sistema AgroRisk Peravia")
    st.markdown(
        f"**Ministerio de Agricultura — Zona Peravia · Baní** &nbsp;·&nbsp; "
        f"{date.today().strftime('%d de %B de %Y').capitalize()}"
    )

    st.markdown("---")

    # ── Condiciones climáticas ─────────────────────────────────────
    clima = _cargar_clima()

    # Tarjetas climáticas
    c1, c2, c3, c4, c5 = st.columns(5)
    _clima_card(c1, "Temp. Max.", f"{clima['temp_max']} °C", "#E53935")
    _clima_card(c2, "Temp. Min.", f"{clima['temp_min']} °C", "#1E88E5")
    _clima_card(c3, "Temp. Media", f"{clima['temp_media']} °C", "#F57C00")
    _clima_card(c4, "Humedad Rel.", f"{clima['humedad']} %", "#0097A7")
    _clima_card(c5, "Precipitacion", f"{clima['precipitacion']} mm", "#5C6BC0")

    if clima["source"] == "fallback":
        st.warning(
            "API climatica no disponible — se muestran valores de referencia ONAMET."
        )
    else:
        st.caption(
            f"Datos en tiempo real: Open-Meteo — Bani (lat=18.28, lon=-70.33) "
            f"· Fuente: {clima['source'].upper()}"
        )

    col_btn, _ = st.columns([2, 6])
    with col_btn:
        if st.button("Actualizar datos climaticos"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")

    # ── Prediccion ─────────────────────────────────────────────────
    mes_actual  = date.today().month
    feno_actual = _mes_a_feno(mes_actual)
    resultados  = predictor.predict(
        temp=clima["temp_media"],
        hum=clima["humedad"],
        lluvia=clima["precipitacion"],
        dias_sin_lluvia=0 if clima["precipitacion"] > 0.5 else 3,
        fenologia=feno_actual,
        mes=mes_actual,
    )

    guardar_prediccion(
        clima={
            "temperatura":      clima["temp_media"],
            "humedad":          clima["humedad"],
            "precipitacion":    clima["precipitacion"],
            "dias_sin_lluvia":  0 if clima["precipitacion"] > 0.5 else 3,
            "fenologia":        feno_actual,
            "mes":              mes_actual,
        },
        resultados=resultados,
        fuente="api" if clima["source"] != "fallback" else "fallback",
    )

    # ── Gauge charts ───────────────────────────────────────────────
    st.markdown("### Indices de Riesgo Fitosanitario — Dia Actual")
    cols = st.columns(4)
    for i, (amenaza, label) in enumerate(AMENAZA_LABEL.items()):
        d = resultados[amenaza]
        with cols[i]:
            fig = _gauge(d["score"], label, d["color"])
            st.plotly_chart(fig, use_container_width=True, key=f"gauge_{amenaza}")
            st.markdown(
                f'<div style="text-align:center;margin-top:-18px;">'
                f'<span style="background:{d["color"]};color:white;padding:3px 12px;'
                f'border-radius:12px;font-size:0.78rem;font-weight:700;">{d["nivel"]}</span>'
                f'<div style="font-size:0.73rem;color:#888;margin-top:4px;">'
                f'Prob. 7 dias: {d["prob_7d"]}%</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Radar + mini-resumen ───────────────────────────────────────
    col_r, col_sum = st.columns([2, 1])
    with col_r:
        st.markdown("### Perfil de Riesgo Global")
        _render_radar(resultados)
    with col_sum:
        st.markdown("### Resumen Ejecutivo")
        st.markdown(f"**Etapa fenologica:** {FENOLOGIA_LABELS[feno_actual]}")
        st.markdown(f"**Temporada:** {'Lluviosa' if mes_actual in range(5,12) else 'Seca'}")
        st.markdown("**Prioridad de atencion:**")
        ordered = sorted(resultados, key=lambda a: resultados[a]["score"], reverse=True)
        for rank, am in enumerate(ordered, 1):
            d = resultados[am]
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0;">'
                f'<span style="background:{d["color"]};color:white;border-radius:50%;'
                f'width:22px;height:22px;display:inline-flex;align-items:center;'
                f'justify-content:center;font-size:0.7rem;font-weight:700;">{rank}</span>'
                f'<span style="font-size:0.88rem;">{AMENAZA_LABEL[am]}</span>'
                f'<span style="font-size:0.75rem;color:#888;">{d["score"]:.0f}/100</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Alertas activas ────────────────────────────────────────────
    alertas = obtener_alertas_activas(20)
    st.markdown(f"### Alertas Activas ({len(alertas)})")
    if not alertas:
        st.success("No hay alertas activas en este momento.")
    else:
        for alerta in alertas:
            nivel  = alerta["nivel"]
            color  = "#F44336" if nivel == "Alto" else "#7B1FA2"
            label  = AMENAZA_LABEL.get(alerta["amenaza"], alerta["amenaza"])
            st.markdown(
                f'<div style="background:#FFF3E0;border-left:4px solid {color};'
                f'padding:10px 16px;border-radius:6px;margin-bottom:8px;">'
                f"<strong>{label}</strong> — Nivel: "
                f'<span style="background:{color};color:white;padding:2px 8px;'
                f'border-radius:10px;font-size:0.78rem;">{nivel}</span>'
                f' &nbsp; Score: {alerta["score"]:.1f}'
                f'<span style="color:#999;font-size:0.78rem;float:right;">'
                f'{alerta["timestamp"]}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )
        col_b, _ = st.columns([2, 6])
        with col_b:
            if st.button("Marcar alertas como vistas"):
                marcar_alertas_vistas()
                st.rerun()

    # ── Recomendaciones ────────────────────────────────────────────
    amenazas_activas = [a for a in resultados if resultados[a]["nivel"] in ("Medio","Alto","Critico")]
    if amenazas_activas:
        st.markdown("---")
        st.markdown("### Recomendaciones para Hoy")
        for amenaza in amenazas_activas:
            d = resultados[amenaza]
            with st.expander(
                f"{AMENAZA_LABEL[amenaza]} — Nivel {d['nivel']} ({d['score']:.0f}/100)"
            ):
                st.write(d["recomendacion"])

    st.markdown(
        '<div class="footer-bar">'
        "Modelo AgroRisk v1.0 &nbsp;·&nbsp; Datos: Open-Meteo / ONAMET "
        "&nbsp;·&nbsp; Zona: Peravia — Bani, RD"
        "</div>",
        unsafe_allow_html=True,
    )


# ── Helpers ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Obteniendo datos climaticos...")
def _cargar_clima():
    return fetch_today()


def _clima_card(col, titulo: str, valor: str, color: str) -> None:
    with col:
        st.markdown(
            f'<div style="background:white;border-radius:10px;padding:12px 14px;'
            f'border-top:4px solid {color};box-shadow:0 2px 8px rgba(0,0,0,0.07);'
            f'text-align:center;">'
            f'<div style="font-size:0.72rem;color:#888;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:0.5px;">{titulo}</div>'
            f'<div style="font-size:1.5rem;font-weight:800;color:#1A1A1A;margin-top:4px;">'
            f'{valor}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _gauge(score: float, label: str, color: str) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": label, "font": {"size": 12, "color": "#333"}},
        number={"font": {"size": 22, "color": color}, "suffix": ""},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#ccc",
                     "tickfont": {"size": 9}},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "white",
            "borderwidth": 1,
            "bordercolor": "#eee",
            "steps": [
                {"range": [0,  25],  "color": "#E8F5E9"},
                {"range": [25, 50],  "color": "#FFF8E1"},
                {"range": [50, 75],  "color": "#FFEBEE"},
                {"range": [75, 100], "color": "#F3E5F5"},
            ],
            "threshold": {
                "line": {"color": color, "width": 3},
                "thickness": 0.8,
                "value": score,
            },
        },
    ))
    fig.update_layout(
        height=200,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _mes_a_feno(mes: int) -> int:
    return {1:2,2:2,3:3,4:3,5:3,6:4,7:4,8:4,9:4,10:0,11:0,12:1}.get(mes, 0)


def _render_radar(resultados: dict) -> None:
    labels = [AMENAZA_LABEL[a] for a in AMENAZA_LABEL]
    scores = [resultados[a]["score"] for a in AMENAZA_LABEL]
    labels_r = labels + [labels[0]]
    scores_r  = scores + [scores[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=scores_r, theta=labels_r,
        fill="toself",
        fillcolor="rgba(27,94,32,0.18)",
        line=dict(color="#1B5E20", width=2.5),
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0,100],
                            tickfont={"size":8}, gridcolor="#ddd"),
            angularaxis=dict(tickfont={"size":11}),
            bgcolor="#F9FBF9",
        ),
        showlegend=False,
        height=340,
        margin=dict(l=50, r=50, t=20, b=20),
        title=dict(
            text="Zona: Peravia — Bani  |  Modelo AgroRisk v1.0",
            font={"size":10,"color":"#888"}, x=0.5,
        ),
    )
    st.plotly_chart(fig, use_container_width=True)
