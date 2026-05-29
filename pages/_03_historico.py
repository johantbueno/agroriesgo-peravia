"""
Historico v2 — Heatmap de calendario + líneas + correlaciones.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

from core.predictor import AgroRiskPredictor

CSV_PATH = Path(__file__).parent.parent / "data" / "peravia_historico.csv"

AMENAZA_LABEL = {
    "mosca":        "Mosca de las Frutas",
    "trips":        "Trips",
    "antracnosis":  "Antracnosis",
    "oidio":        "Oidio",
}
COLORES = {
    "mosca":       "#E53935",
    "trips":       "#FB8C00",
    "antracnosis": "#1E88E5",
    "oidio":       "#8E24AA",
}
MESES_ES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]


def render(predictor: AgroRiskPredictor) -> None:
    st.markdown("## Analisis Historico de Riesgo")
    st.markdown("Serie temporal 2022–2024 · Zona Peravia — Bani, RD")
    st.markdown("---")

    if not CSV_PATH.exists():
        st.warning("Datos historicos no disponibles. Reinicie la aplicacion.")
        return

    df_raw = pd.read_csv(CSV_PATH, parse_dates=["fecha"])
    df     = predictor.predict_batch(df_raw)
    df["anio_mes"] = df["fecha"].dt.to_period("M").dt.to_timestamp()
    df["anio"]     = df["fecha"].dt.year
    df["mes_num"]  = df["fecha"].dt.month

    df_mes = (
        df.groupby(["anio_mes", "anio", "mes_num"])
        .agg(
            temp_media    =("temperatura",       "mean"),
            hum_media     =("humedad",           "mean"),
            lluvia_total  =("precipitacion",     "sum"),
            mosca         =("pred_mosca",         "mean"),
            trips         =("pred_trips",         "mean"),
            antracnosis   =("pred_antracnosis",   "mean"),
            oidio         =("pred_oidio",         "mean"),
        )
        .reset_index()
        .round(1)
    )

    # ── Filtros ────────────────────────────────────────────────────
    col_a, col_b = st.columns([3, 3])
    with col_a:
        amenaza_sel = st.multiselect(
            "Amenazas",
            list(AMENAZA_LABEL.keys()),
            default=list(AMENAZA_LABEL.keys()),
            format_func=lambda x: AMENAZA_LABEL[x],
        )
    with col_b:
        anios = sorted(df["anio"].unique())
        anios_sel = st.multiselect("Años", anios, default=anios)

    df_fil = df_mes[df_mes["anio"].isin(anios_sel)].copy()

    st.markdown("---")

    # ── Tabs de secciones ─────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "Evolucion Temporal", "Heatmap de Calendario",
        "Correlaciones Climaticas", "Tabla de Datos",
    ])

    # ── Tab 1: Líneas temporales ───────────────────────────────────
    with tab1:
        if amenaza_sel:
            fig = go.Figure()
            for am in amenaza_sel:
                fig.add_trace(go.Scatter(
                    x=df_fil["anio_mes"], y=df_fil[am],
                    name=AMENAZA_LABEL[am],
                    line=dict(color=COLORES[am], width=2.5),
                    mode="lines+markers",
                    marker=dict(size=5),
                ))
            # Zonas de umbral
            for y0, y1, color, label in [
                (0,25,"rgba(76,175,80,0.06)","Bajo"),
                (25,50,"rgba(255,152,0,0.06)","Medio"),
                (50,75,"rgba(244,67,54,0.06)","Alto"),
                (75,100,"rgba(123,31,162,0.06)","Critico"),
            ]:
                fig.add_hrect(y0=y0, y1=y1, fillcolor=color, line_width=0,
                              annotation_text=label,
                              annotation_position="right",
                              annotation=dict(font_size=9, font_color="#bbb"))

            fig.update_layout(
                height=400, yaxis=dict(title="Indice promedio mensual (0–100)", range=[0,105]),
                xaxis=dict(title=""),
                legend=dict(orientation="h", y=-0.15),
                plot_bgcolor="#F9FBF9",
                margin=dict(l=20,r=20,t=40,b=60),
                title=dict(
                    text="Evolucion Mensual · Zona: Peravia — Bani · Modelo AgroRisk v1.0",
                    font={"size":10,"color":"#888"}, x=0.5,
                ),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Tab 2: Heatmap calendario ──────────────────────────────────
    with tab2:
        st.markdown("##### Mapa de Calor de Riesgo por Mes y Año")
        am_heat = st.selectbox(
            "Amenaza para el heatmap",
            list(AMENAZA_LABEL.keys()),
            format_func=lambda x: AMENAZA_LABEL[x],
            key="heat_amenaza",
        )

        pivot = df_mes[df_mes["anio"].isin(anios_sel)].pivot_table(
            index="anio", columns="mes_num", values=am_heat, aggfunc="mean"
        ).round(1)

        fig_heat = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[MESES_ES[m-1] for m in pivot.columns],
            y=[str(y) for y in pivot.index],
            colorscale=[
                [0.00, "#E8F5E9"],
                [0.25, "#FFF9C4"],
                [0.50, "#FFCCBC"],
                [0.75, "#EF9A9A"],
                [1.00, "#7B1FA2"],
            ],
            zmin=0, zmax=100,
            text=pivot.values.round(1),
            texttemplate="%{text}",
            textfont={"size": 11},
            colorbar=dict(
                title="Indice",
                tickvals=[0,25,50,75,100],
                ticktext=["Bajo","Medio","Alto","Critico","Max"],
            ),
        ))
        fig_heat.update_layout(
            height=280,
            title=dict(
                text=f"Riesgo: {AMENAZA_LABEL[am_heat]} · Zona Peravia — Bani",
                font={"size":11,"color":"#444"}, x=0.5,
            ),
            xaxis=dict(title="Mes"),
            yaxis=dict(title="Año"),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # Picos históricos
        st.markdown("**Picos historicos de riesgo:**")
        for am in (amenaza_sel or list(AMENAZA_LABEL.keys())):
            fila_max = df_mes.loc[df_mes[am].idxmax()]
            mes_nombre = MESES_ES[int(fila_max["mes_num"]) - 1]
            st.markdown(
                f'<span style="background:{COLORES[am]};color:white;padding:3px 10px;'
                f'border-radius:10px;font-size:0.8rem;margin-right:8px;">'
                f'{AMENAZA_LABEL[am]}: {fila_max[am]:.1f}/100 '
                f'({mes_nombre} {int(fila_max["anio"])})'
                f'</span>',
                unsafe_allow_html=True,
            )
        st.markdown("")

    # ── Tab 3: Correlaciones ───────────────────────────────────────
    with tab3:
        if not amenaza_sel:
            st.info("Seleccione al menos una amenaza.")
        else:
            am_s = amenaza_sel[0]
            col1, col2 = st.columns(2)
            with col1:
                fig_t = px.scatter(
                    df_fil, x="temp_media", y=am_s,
                    color_discrete_sequence=[COLORES[am_s]],
                    labels={"temp_media":"Temperatura media (°C)",
                            am_s:f"Riesgo {AMENAZA_LABEL[am_s]}"},
                    title=f"Temperatura vs {AMENAZA_LABEL[am_s]}",
                    trendline="ols",
                )
                fig_t.update_layout(height=300, plot_bgcolor="#F9FBF9")
                st.plotly_chart(fig_t, use_container_width=True)

            with col2:
                fig_h = px.scatter(
                    df_fil, x="hum_media", y=am_s,
                    color_discrete_sequence=[COLORES[am_s]],
                    labels={"hum_media":"Humedad media (%)",
                            am_s:f"Riesgo {AMENAZA_LABEL[am_s]}"},
                    title=f"Humedad vs {AMENAZA_LABEL[am_s]}",
                    trendline="ols",
                )
                fig_h.update_layout(height=300, plot_bgcolor="#F9FBF9")
                st.plotly_chart(fig_h, use_container_width=True)

            # Matriz de correlacion
            st.markdown("##### Matriz de Correlacion")
            cols_corr = ["temp_media","hum_media","lluvia_total"] + list(AMENAZA_LABEL.keys())
            labels_corr = ["Temperatura","Humedad","Lluvia"] + [AMENAZA_LABEL[a] for a in AMENAZA_LABEL]
            corr = df_fil[cols_corr].corr().round(2)
            fig_corr = go.Figure(go.Heatmap(
                z=corr.values,
                x=labels_corr, y=labels_corr,
                colorscale="RdYlGn",
                zmin=-1, zmax=1,
                text=corr.values,
                texttemplate="%{text:.2f}",
                textfont={"size":10},
                colorbar=dict(title="r"),
            ))
            fig_corr.update_layout(
                height=350, margin=dict(l=10,r=10,t=20,b=10),
                title=dict(text="Correlacion Pearson entre variables",
                           font={"size":11}, x=0.5),
            )
            st.plotly_chart(fig_corr, use_container_width=True)

    # ── Tab 4: Tabla exportable ────────────────────────────────────
    with tab4:
        cols_show = (
            ["anio_mes","temp_media","hum_media","lluvia_total"]
            + [a for a in AMENAZA_LABEL if a in (amenaza_sel or list(AMENAZA_LABEL.keys()))]
        )
        df_tabla = df_fil[cols_show].copy()
        df_tabla.columns = (
            ["Mes","Temp. Media °C","Hum. Media %","Lluvia Total mm"]
            + [AMENAZA_LABEL[a] for a in AMENAZA_LABEL
               if a in (amenaza_sel or list(AMENAZA_LABEL.keys()))]
        )
        df_tabla["Mes"] = df_tabla["Mes"].dt.strftime("%b %Y")
        st.dataframe(df_tabla, use_container_width=True, hide_index=True)

        st.download_button(
            "Exportar a CSV",
            data=df_tabla.to_csv(index=False).encode("utf-8"),
            file_name=f"agrorisk_historico_{pd.Timestamp.today().date()}.csv",
            mime="text/csv",
        )
