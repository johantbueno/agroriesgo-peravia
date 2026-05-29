"""
Mapa Coroplético — AgroRisk Peravia v3.
Vista nacional RD + detalle Peravia + análisis espacial.
Autor: Dr. Johan Tapia, PhD
"""
from __future__ import annotations
from datetime import date
import plotly.graph_objects as go
import streamlit as st

from core.predictor import AgroRiskPredictor
from core.climate_api import fetch_today
from core.data_generator import FENOLOGIA_LABELS
from core.maps import (
    calcular_riesgo_nacional, calcular_riesgo_zonas,
    mapa_nacional_dr, mapa_peravia_detalle, mapa_densidad_riesgo,
    PROVINCIAS_DR, ZONAS_PERAVIA, _NIVEL_COLOR,
)

AMENAZA_LABEL = {
    "mosca": "Mosca de las Frutas",
    "trips": "Trips",
    "antracnosis": "Antracnosis",
    "oidio": "Oidio",
}
_MES_A_FENO = {1:2,2:2,3:3,4:3,5:3,6:4,7:4,8:4,9:4,10:0,11:0,12:1}


def render(predictor: AgroRiskPredictor) -> None:
    st.markdown("## Mapa de Riesgo Fitosanitario")
    st.markdown(
        "Visualización geoespacial · Mango · República Dominicana "
        "| Zona foco: **Peravia — Baní** (lat 18.28°N, lon 70.33°W)"
    )
    st.markdown("---")

    # ── Calcular riesgo actual ────────────────────────────────────
    clima   = fetch_today()
    mes     = date.today().month
    feno    = _MES_A_FENO.get(mes, 0)

    resultados = predictor.predict(
        temp=clima["temp_media"], hum=clima["humedad"],
        lluvia=clima["precipitacion"],
        dias_sin_lluvia=0 if clima["precipitacion"] > 0.5 else 3,
        fenologia=feno, mes=mes,
    )

    datos_prov  = calcular_riesgo_nacional(resultados)
    zonas_peravia = calcular_riesgo_zonas(resultados)

    # ── KPI header ────────────────────────────────────────────────
    prov_alto   = sum(1 for p in datos_prov if p["nivel"] in ("Alto", "Critico"))
    area_riesgo = sum(p["mango_ha"] for p in datos_prov if p["nivel"] in ("Alto", "Critico"))
    zona_max    = max(zonas_peravia, key=lambda z: z["riesgo_max"])
    amenaza_max = max(resultados, key=lambda a: resultados[a]["score"])

    k1, k2, k3, k4 = st.columns(4)
    _kpi(k1, "Provincias en Alerta", str(prov_alto), "/32", "#F44336")
    _kpi(k2, "Ha Mango en Riesgo", f"{area_riesgo:,}", "ha", "#FF9800")
    _kpi(k3, "Zona Critica Peravia", zona_max["zona"], zona_max["nivel"], _NIVEL_COLOR[zona_max["nivel"]])
    _kpi(k4, "Amenaza Principal", AMENAZA_LABEL[amenaza_max],
         f"{resultados[amenaza_max]['score']:.0f}/100", _NIVEL_COLOR[resultados[amenaza_max]["nivel"]])

    st.markdown("---")

    # ── Tabs de mapa ─────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "Vista Nacional RD",
        "Detalle Peravia",
        "Mapa de Calor",
        "Analisis Espacial",
    ])

    # ─── Tab 1: Mapa nacional ───────────────────────────────────
    with tab1:
        col_ctrl, col_map = st.columns([1, 3])
        with col_ctrl:
            st.markdown("##### Controles")
            amenaza_sel = st.selectbox(
                "Amenaza",
                list(AMENAZA_LABEL.keys()),
                format_func=lambda x: AMENAZA_LABEL[x],
                key="mapa_amenaza",
            )
            region_sel = st.multiselect(
                "Región",
                ["Sur", "Suroeste", "Cibao", "Norte", "Noroeste", "Este", "Nordeste"],
                default=["Sur", "Suroeste", "Cibao"],
            )
            min_ha = st.slider("Area mínima (ha)", 0, 5000, 0, 500)

            # Leyenda
            st.markdown("##### Leyenda")
            for nivel, color in _NIVEL_COLOR.items():
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0;">'
                    f'<div style="width:14px;height:14px;border-radius:50%;'
                    f'background:{color};"></div>'
                    f'<span style="font-size:0.82rem;">{nivel}</span></div>',
                    unsafe_allow_html=True,
                )

            # Top 5 provincias
            st.markdown("##### Top 5 Riesgo")
            top5 = sorted(datos_prov, key=lambda p: p["riesgo_max"], reverse=True)[:5]
            for p in top5:
                c = _NIVEL_COLOR[p["nivel"]]
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'border-left:3px solid {c};padding:3px 8px;margin:2px 0;'
                    f'font-size:0.8rem;">'
                    f'<span>{p["nombre"]}</span>'
                    f'<strong style="color:{c};">{p["riesgo_max"]:.0f}</strong>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        with col_map:
            # Filtrar provincias
            datos_filtrados = [
                p for p in datos_prov
                if (not region_sel or p["region"] in region_sel)
                and p["mango_ha"] >= min_ha
            ]
            if datos_filtrados:
                # Ajustar scores según amenaza seleccionada
                for p in datos_filtrados:
                    p["riesgo_max"] = p["scores"].get(amenaza_sel, p["riesgo_max"])
                    p["nivel"] = _score_to_nivel(p["riesgo_max"])

                fig_nac = mapa_nacional_dr(datos_filtrados, amenaza_sel)
                st.plotly_chart(fig_nac, use_container_width=True)
                st.caption(
                    f"Mostrando {len(datos_filtrados)} provincias · "
                    f"Amenaza: {AMENAZA_LABEL[amenaza_sel]} · "
                    f"Datos: Modelo AgroRisk + Open-Meteo · "
                    f"Créditos: Dr. Johan Tapia, PhD"
                )
            else:
                st.info("Sin datos para los filtros seleccionados.")

    # ─── Tab 2: Detalle Peravia ─────────────────────────────────
    with tab2:
        col_map2, col_det = st.columns([3, 1])
        with col_map2:
            fig_per = mapa_peravia_detalle(zonas_peravia)
            st.plotly_chart(fig_per, use_container_width=True)
            st.caption(
                "Zonas agrícolas de mango en Peravia · "
                "Coordenadas: lat 18.28°N, lon 70.33°W · "
                "Modelo AgroRisk v3 · Dr. Johan Tapia, PhD"
            )

        with col_det:
            st.markdown("##### Zonas por Nivel")
            for nivel in ["Critico", "Alto", "Medio", "Bajo"]:
                zonas_n = [z for z in zonas_peravia if z["nivel"] == nivel]
                if zonas_n:
                    c = _NIVEL_COLOR[nivel]
                    st.markdown(
                        f'<div style="background:{c}15;border-left:3px solid {c};'
                        f'padding:8px;border-radius:4px;margin-bottom:8px;">'
                        f'<div style="font-weight:700;color:{c};font-size:0.8rem;">'
                        f'{nivel} ({len(zonas_n)})</div>',
                        unsafe_allow_html=True,
                    )
                    for z in zonas_n:
                        st.markdown(
                            f'<div style="font-size:0.78rem;margin-top:3px;">'
                            f'• {z["zona"]} ({z["riesgo_max"]:.0f})</div>',
                            unsafe_allow_html=True,
                        )
                    st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("##### Geolocalizacion")
            st.markdown(
                '<div style="background:#E8F5E9;border-radius:8px;padding:10px;">'
                '<div style="font-size:0.8rem;color:#1B5E20;">'
                '<strong>Peravia — Baní</strong><br>'
                'Latitud: 18° 16\' 47" N<br>'
                'Longitud: 70° 19\' 46" O<br>'
                'Elevación: 85 m.s.n.m.<br>'
                'Área: 792 km²<br>'
                'Clima: BSh (Árido-cálido)<br>'
                'Precipitación: 850 mm/año'
                '</div></div>',
                unsafe_allow_html=True,
            )

    # ─── Tab 3: Mapa de calor ───────────────────────────────────
    with tab3:
        st.markdown("##### Distribución Espacial de Riesgo por Amenaza")
        amenaza_heat = st.selectbox(
            "Amenaza para mapa de calor",
            list(AMENAZA_LABEL.keys()),
            format_func=lambda x: AMENAZA_LABEL[x],
            key="heat_am",
        )
        fig_heat = mapa_densidad_riesgo(zonas_peravia, amenaza_heat)
        st.plotly_chart(fig_heat, use_container_width=True)
        st.caption(
            f"Distribución de intensidad — {AMENAZA_LABEL[amenaza_heat]} · "
            f"Zona Peravia, Baní · AgroRisk v3"
        )

    # ─── Tab 4: Análisis espacial ───────────────────────────────
    with tab4:
        st.markdown("##### Ranking de Zonas — Peravia")
        _render_ranking_zonas(zonas_peravia)

        st.markdown("---")
        st.markdown("##### Distribución Regional — República Dominicana")
        _render_barras_regiones(datos_prov)


# ── Helpers ────────────────────────────────────────────────────────────────

def _kpi(col, titulo, valor, sub, color):
    with col:
        st.markdown(
            f'<div style="background:white;border-radius:10px;padding:14px 16px;'
            f'border-top:4px solid {color};box-shadow:0 2px 8px rgba(0,0,0,0.07);">'
            f'<div style="font-size:0.7rem;color:#888;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:0.5px;">{titulo}</div>'
            f'<div style="font-size:1.35rem;font-weight:800;color:#1A1A1A;'
            f'margin-top:4px;">{valor}</div>'
            f'<div style="font-size:0.75rem;color:{color};font-weight:600;">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _score_to_nivel(s):
    if s < 25: return "Bajo"
    if s < 50: return "Medio"
    if s < 75: return "Alto"
    return "Critico"


def _render_ranking_zonas(zonas):
    import plotly.express as px
    import pandas as pd

    df = pd.DataFrame([
        {"Zona": z["zona"], "Riesgo": z["riesgo_max"],
         "Nivel": z["nivel"], "Ha": z["ha"],
         "Mosca": z["scores"].get("mosca", 0),
         "Trips": z["scores"].get("trips", 0),
         "Antracnosis": z["scores"].get("antracnosis", 0),
         "Oidio": z["scores"].get("oidio", 0),
         }
        for z in sorted(zonas, key=lambda z: z["riesgo_max"], reverse=True)
    ])

    fig = go.Figure()
    for amenaza, color in [
        ("Mosca", "#E53935"), ("Trips", "#FB8C00"),
        ("Antracnosis", "#1E88E5"), ("Oidio", "#8E24AA"),
    ]:
        fig.add_trace(go.Bar(
            name=amenaza, x=df["Zona"], y=df[amenaza],
            marker_color=color, opacity=0.82,
        ))
    fig.update_layout(
        barmode="group",
        height=340,
        xaxis=dict(tickangle=-30),
        yaxis=dict(title="Índice de riesgo", range=[0, 100]),
        legend=dict(orientation="h", y=-0.35),
        plot_bgcolor="#F9FBF9",
        margin=dict(l=20, r=20, t=20, b=80),
        title=dict(text="Comparativa de amenazas por zona · Peravia",
                   font={"size": 11, "color": "#555"}, x=0.5),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_barras_regiones(datos_prov):
    import pandas as pd
    from collections import defaultdict

    regiones: dict = defaultdict(lambda: {"ha": 0, "riesgo": [], "provincias": 0})
    for p in datos_prov:
        r = p["region"]
        regiones[r]["ha"] += p["mango_ha"]
        regiones[r]["riesgo"].append(p["riesgo_max"])
        regiones[r]["provincias"] += 1

    regs = sorted(regiones.items(), key=lambda x: -sum(x[1]["riesgo"]) / len(x[1]["riesgo"]))
    nombres  = [r[0] for r in regs]
    avg_risk = [round(sum(r[1]["riesgo"]) / len(r[1]["riesgo"]), 1) for r in regs]
    total_ha = [r[1]["ha"] for r in regs]
    colors   = [_NIVEL_COLOR[_score_to_nivel(r)] for r in avg_risk]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=nombres, y=avg_risk, name="Riesgo Promedio",
        marker_color=colors, text=[f"{r:.1f}" for r in avg_risk],
        textposition="outside",
    ))
    fig.add_trace(go.Scatter(
        x=nombres, y=[h / 100 for h in total_ha],
        name="Área Mango (×100 ha)",
        mode="lines+markers",
        line=dict(color="#1B5E20", width=2, dash="dot"),
        yaxis="y2",
    ))
    fig.update_layout(
        yaxis=dict(title="Riesgo promedio (0–100)", range=[0, 110]),
        yaxis2=dict(title="Área mango (×100 ha)", overlaying="y",
                    side="right", showgrid=False),
        legend=dict(orientation="h", y=-0.2),
        height=320,
        plot_bgcolor="#F9FBF9",
        margin=dict(l=20, r=40, t=20, b=60),
        title=dict(
            text="Riesgo promedio y área de cultivo por región · República Dominicana",
            font={"size": 11, "color": "#555"}, x=0.5,
        ),
    )
    st.plotly_chart(fig, use_container_width=True)
