"""
Reporte Fitosanitario Diario v3 — Power BI Style.
Autor: Dr. Johan Tapia, PhD | AgroRisk Peravia
"""
from __future__ import annotations
from datetime import date, datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from pathlib import Path

from core.climate_api import fetch_today, fetch_forecast_week
from core.data_generator import FENOLOGIA_LABELS, FENOLOGIA_MAP
from core.predictor import AgroRiskPredictor
from core.asistente_ia import AgroAsistente

CSV_PATH = Path(__file__).parent.parent / "data" / "peravia_historico.csv"

AMENAZA_LABEL  = {"mosca":"Mosca de las Frutas","trips":"Trips",
                  "antracnosis":"Antracnosis","oidio":"Oidio"}
AMENAZA_COLOR  = {"mosca":"#E53935","trips":"#FB8C00",
                  "antracnosis":"#1E88E5","oidio":"#8E24AA"}
NIVEL_TAG      = {"Bajo":"BAJO","Medio":"MEDIO","Alto":"ALTO","Critico":"CRITICO"}
NIVEL_COLOR    = {"Bajo":"#4CAF50","Medio":"#FF9800","Alto":"#F44336","Critico":"#7B1FA2"}


def render(predictor: AgroRiskPredictor) -> None:
    st.markdown("## Reporte Ejecutivo Fitosanitario")
    st.markdown(
        "Análisis integrado · Modelo AgroRisk v3 · Zona Peravia — Baní | "
        "**Dr. Johan Tapia, PhD** — Ministerio de Agricultura RD"
    )
    st.markdown("---")

    # ── Parámetros del reporte ────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        tecnico = st.text_input("Técnico responsable",
                                value="Dr. Johan Tapia, PhD")
        zona    = st.text_input("Zona / Parcela",
                                value="Sector Mango — Peravia, Baní")
    with col2:
        feno_sel   = st.selectbox("Etapa fenológica actual", FENOLOGIA_LABELS, index=2)
        mes_actual = date.today().month
    with col3:
        incluir_ia   = st.checkbox("Incluir interpretación IA", value=True)
        incluir_pron = st.checkbox("Incluir pronóstico climático", value=True)

    clima    = fetch_today()
    feno_val = FENOLOGIA_MAP[feno_sel]
    resultado = predictor.predict(
        temp=clima["temp_media"], hum=clima["humedad"],
        lluvia=clima["precipitacion"],
        dias_sin_lluvia=0 if clima["precipitacion"] > 0.5 else 3,
        fenologia=feno_val, mes=mes_actual,
    )

    # ── Cargar histórico para comparativas ────────────────────────
    df_hist = _cargar_hist_mes(mes_actual)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # BLOQUE 1 — PANEL KPI (Power BI style)
    # ══════════════════════════════════════════════════════════════
    st.markdown("### Panel de Indicadores Clave")
    _render_kpi_panel(resultado, clima, df_hist)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # BLOQUE 2 — DASHBOARD COMBINADO (Power BI: gauges + barras)
    # ══════════════════════════════════════════════════════════════
    st.markdown("### Dashboard Integrado de Riesgo")
    _render_dashboard_combinado(resultado)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # BLOQUE 3 — ANÁLISIS FACTORIAL (Treemap + Bullet + Waterfall)
    # ══════════════════════════════════════════════════════════════
    st.markdown("### Análisis Factorial de Riesgo")
    col_t, col_b = st.columns([1, 1])
    with col_t:
        _render_treemap(resultado, predictor)
    with col_b:
        _render_bullet_chart(resultado)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # BLOQUE 4 — COMPARATIVA VS HISTÓRICO
    # ══════════════════════════════════════════════════════════════
    if df_hist is not None:
        st.markdown("### Comparativa vs. Histórico (mismo mes)")
        _render_comparativa_historico(resultado, df_hist, predictor)
        st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # BLOQUE 5 — PRONÓSTICO 7 DÍAS
    # ══════════════════════════════════════════════════════════════
    if incluir_pron:
        st.markdown("### Pronóstico Climático — Próximos 7 Días")
        _render_pronostico(predictor, feno_val, mes_actual)
        st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # BLOQUE 6 — INTERPRETACIÓN IA
    # ══════════════════════════════════════════════════════════════
    if incluir_ia:
        st.markdown("### Interpretación del Asistente IA")
        asistente = AgroAsistente()
        analisis  = asistente.analizar(resultado, clima, feno_val, mes_actual)
        _render_interpretacion_ia(analisis, resultado, clima, df_hist, predictor)
        st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # BLOQUE 7 — REPORTE EXPORTABLE
    # ══════════════════════════════════════════════════════════════
    st.markdown("### Exportar Reporte")
    if st.button("Generar Reporte Completo", type="primary"):
        txt = _construir_reporte_completo(
            clima, resultado, feno_sel, zona, tecnico,
            df_hist, analisis if incluir_ia else None
        )
        st.session_state["reporte_txt"] = txt

    if "reporte_txt" in st.session_state:
        st.text_area(
            "Texto listo para copiar (Ctrl+A → Ctrl+C)",
            st.session_state["reporte_txt"], height=500,
        )
        st.download_button(
            "Descargar .txt",
            data=st.session_state["reporte_txt"].encode("utf-8"),
            file_name=f"reporte_agrorisk_{date.today().isoformat()}.txt",
            mime="text/plain",
        )
        st.caption("Listo para WhatsApp, correo institucional o archivo.")


# ── Bloque 1: KPI Panel ────────────────────────────────────────────────────

def _render_kpi_panel(resultado, clima, df_hist):
    amenaza_max = max(resultado, key=lambda a: resultado[a]["score"])
    d_max = resultado[amenaza_max]
    score_max = d_max["score"]

    # Calcular tendencia vs histórico del mismo mes
    trend_str = "—"
    if df_hist is not None:
        hist_mean = df_hist[f"pred_{amenaza_max}"].mean() if f"pred_{amenaza_max}" in df_hist else None
        if hist_mean:
            delta = score_max - hist_mean
            trend_str = f"{'▲' if delta > 0 else '▼'} {abs(delta):.1f} vs promedio histórico"

    # 6 KPI cards
    k = st.columns(6)
    _kpi_card(k[0], "Temp. Media", f"{clima['temp_media']}°C",
              "Baní hoy", "#E53935")
    _kpi_card(k[1], "Humedad Rel.", f"{clima['humedad']}%",
              "Open-Meteo API", "#0097A7")
    _kpi_card(k[2], "Precipitación", f"{clima['precipitacion']}mm",
              "Acumulado hoy", "#5C6BC0")
    _kpi_card(k[3], "Amenaza Crítica", AMENAZA_LABEL[amenaza_max],
              f"Índice {score_max:.0f}/100", NIVEL_COLOR[d_max["nivel"]])
    _kpi_card(k[4], "Nivel Global",
              max(resultado[a]["nivel"] for a in resultado),
              trend_str, NIVEL_COLOR[d_max["nivel"]])
    n_alerta = sum(1 for d in resultado.values() if d["nivel"] in ("Alto","Critico"))
    _kpi_card(k[5], "Amenazas Activas", str(n_alerta),
              "en nivel Alto/Crítico", "#F44336" if n_alerta > 0 else "#4CAF50")


def _kpi_card(col, titulo, valor, sub, color):
    with col:
        st.markdown(
            f'<div style="background:white;border-radius:10px;padding:14px 12px;'
            f'border-top:4px solid {color};box-shadow:0 2px 8px rgba(0,0,0,0.07);'
            f'text-align:center;">'
            f'<div style="font-size:0.68rem;color:#888;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.5px;">{titulo}</div>'
            f'<div style="font-size:1.3rem;font-weight:800;color:#1A1A1A;'
            f'margin:4px 0;">{valor}</div>'
            f'<div style="font-size:0.68rem;color:{color};font-weight:600;">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Bloque 2: Dashboard combinado ─────────────────────────────────────────

def _render_dashboard_combinado(resultado):
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=2, cols=4,
        specs=[
            [{"type":"indicator"},{"type":"indicator"},
             {"type":"indicator"},{"type":"indicator"}],
            [{"colspan":4,"type":"xy"}, None, None, None],
        ],
        vertical_spacing=0.12,
        subplot_titles=("","","","",
                        "Índices de Riesgo — Comparativa por Amenaza"),
    )

    amenazas = list(AMENAZA_LABEL.keys())
    for i, am in enumerate(amenazas):
        d = resultado[am]
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=d["score"],
            title={"text": AMENAZA_LABEL[am], "font": {"size": 10}},
            number={"font": {"size": 18, "color": d["color"]}},
            delta={"reference": 50, "increasing": {"color": "#F44336"},
                   "decreasing": {"color": "#4CAF50"},
                   "font": {"size": 9}},
            gauge={
                "axis": {"range": [0,100], "tickfont": {"size": 7}},
                "bar": {"color": d["color"], "thickness": 0.28},
                "steps": [
                    {"range":[0,25],  "color":"#E8F5E9"},
                    {"range":[25,50], "color":"#FFF8E1"},
                    {"range":[50,75], "color":"#FFEBEE"},
                    {"range":[75,100],"color":"#F3E5F5"},
                ],
                "threshold": {"line":{"color":d["color"],"width":3},
                              "thickness":0.85, "value":d["score"]},
            },
        ), row=1, col=i+1)

    # Barras horizontales con zonas
    fig.add_trace(go.Bar(
        y=[AMENAZA_LABEL[a] for a in amenazas],
        x=[resultado[a]["score"] for a in amenazas],
        orientation="h",
        marker_color=[resultado[a]["color"] for a in amenazas],
        text=[f'{resultado[a]["score"]:.1f} — {resultado[a]["nivel"]}'
              for a in amenazas],
        textposition="outside",
        marker_line_width=0,
    ), row=2, col=1)

    # Líneas de umbral
    for x_val, label, color in [
        (25,"Bajo","#4CAF50"), (50,"Medio","#FF9800"),
        (75,"Alto","#F44336"),
    ]:
        fig.add_vline(x=x_val, line_dash="dot", line_color=color,
                      line_width=1.5, row=2, col=1)
        fig.add_annotation(
            x=x_val, y=3.6, text=label, showarrow=False,
            font=dict(size=8, color=color), row=2, col=1,
        )

    fig.update_xaxes(range=[0, 115], row=2, col=1)
    fig.update_layout(
        height=520, showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F9FBF9",
        margin=dict(l=10, r=20, t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Bloque 3: Treemap + Bullet Chart ──────────────────────────────────────

def _render_treemap(resultado, predictor):
    """Treemap de contribución de factores al riesgo."""
    st.markdown("##### Contribución de Factores de Riesgo")

    amenaza_max = max(resultado, key=lambda a: resultado[a]["score"])
    importancias = predictor.get_feature_importance(amenaza_max)

    feat_labels = {
        "temperatura": "Temperatura",
        "humedad": "Humedad Rel.",
        "precipitacion": "Precipitación",
        "dias_sin_lluvia": "Días Secos",
        "fenologia": "Fenología",
        "mes": "Mes",
        "interaccion_temp_hum": "Int. Temp/Hum",
    }
    if not importancias.empty:
        labels = [feat_labels.get(f, f) for f in importancias.index]
        values = importancias.values * resultado[amenaza_max]["score"]
        parents = ["" for _ in labels]

        fig = go.Figure(go.Treemap(
            labels=labels,
            values=values,
            parents=parents,
            textinfo="label+percent root",
            marker=dict(
                colors=values,
                colorscale=[
                    [0.0, "#E8F5E9"], [0.5, "#FFF9C4"], [1.0, "#FFCCBC"],
                ],
                showscale=False,
            ),
            hovertemplate="<b>%{label}</b><br>Contribución: %{value:.1f}<br>%{percentRoot}<extra></extra>",
        ))
        fig.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=30, b=0),
            title=dict(
                text=f"Factores → {AMENAZA_LABEL[amenaza_max]}",
                font={"size":11,"color":"#444"}, x=0.5,
            ),
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_bullet_chart(resultado):
    """Bullet chart: actual vs umbral vs crítico."""
    st.markdown("##### Posición vs Umbrales")

    amenazas = list(AMENAZA_LABEL.keys())
    fig = go.Figure()

    for i, am in enumerate(amenazas):
        score = resultado[am]["score"]
        # Rango de fondo
        fig.add_trace(go.Bar(
            x=[100], y=[AMENAZA_LABEL[am]],
            orientation="h", base=0,
            marker_color="#F3E5F5", showlegend=False, width=0.5,
        ))
        fig.add_trace(go.Bar(
            x=[75], y=[AMENAZA_LABEL[am]],
            orientation="h", base=0,
            marker_color="#FFEBEE", showlegend=False, width=0.5,
        ))
        fig.add_trace(go.Bar(
            x=[50], y=[AMENAZA_LABEL[am]],
            orientation="h", base=0,
            marker_color="#FFF8E1", showlegend=False, width=0.5,
        ))
        fig.add_trace(go.Bar(
            x=[25], y=[AMENAZA_LABEL[am]],
            orientation="h", base=0,
            marker_color="#E8F5E9", showlegend=False, width=0.5,
        ))
        # Barra actual
        fig.add_trace(go.Bar(
            x=[score], y=[AMENAZA_LABEL[am]],
            orientation="h", base=0,
            marker_color=resultado[am]["color"],
            marker_opacity=0.9, width=0.28,
            text=f'{score:.1f}', textposition="outside",
            showlegend=(i == 0), name="Índice actual",
        ))

    for x_thr, label, color in [(25,"Bajo","#4CAF50"),(50,"Medio","#FF9800"),(75,"Alto","#F44336")]:
        fig.add_vline(x=x_thr, line_dash="dash", line_color=color,
                      line_width=1.5, annotation_text=label,
                      annotation_position="top",
                      annotation_font=dict(size=8, color=color))

    fig.update_layout(
        barmode="overlay",
        xaxis=dict(range=[0,115], title="Índice (0–100)"),
        yaxis=dict(title=""),
        height=280,
        plot_bgcolor="#F9FBF9",
        margin=dict(l=20, r=30, t=30, b=20),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Bloque 4: Comparativa histórica ───────────────────────────────────────

def _render_comparativa_historico(resultado, df_hist, predictor):
    """Gráfico de comparativa actual vs media histórica del mismo mes."""
    df_p = predictor.predict_batch(df_hist)
    hist_means = {am: df_p[f"pred_{am}"].mean() for am in AMENAZA_LABEL}
    hist_std   = {am: df_p[f"pred_{am}"].std()  for am in AMENAZA_LABEL}

    amenazas = list(AMENAZA_LABEL.keys())
    labels   = [AMENAZA_LABEL[a] for a in amenazas]
    actual   = [resultado[a]["score"] for a in amenazas]
    hist_m   = [hist_means[a] for a in amenazas]
    hist_s   = [hist_std[a]   for a in amenazas]

    fig = go.Figure()
    # Banda ±1 std histórica
    fig.add_trace(go.Bar(
        x=labels, y=[2*s for s in hist_s],
        base=[m - s for m, s in zip(hist_m, hist_s)],
        marker_color="rgba(158,158,158,0.2)",
        name="Rango histórico (±1σ)",
        width=0.5,
    ))
    # Media histórica
    fig.add_trace(go.Scatter(
        x=labels, y=hist_m, mode="markers+lines",
        name="Media histórica (mismo mes)",
        line=dict(color="#9E9E9E", dash="dot", width=2),
        marker=dict(size=10, symbol="diamond", color="#9E9E9E"),
    ))
    # Valor actual
    fig.add_trace(go.Bar(
        x=labels, y=actual,
        marker_color=[resultado[a]["color"] for a in amenazas],
        name="Índice actual",
        text=[f"{v:.1f}" for v in actual],
        textposition="outside",
        width=0.4,
    ))

    fig.update_layout(
        barmode="overlay",
        height=340,
        yaxis=dict(range=[0, 110], title="Índice de riesgo (0–100)"),
        legend=dict(orientation="h", y=-0.2),
        plot_bgcolor="#F9FBF9",
        margin=dict(l=20, r=20, t=30, b=60),
        title=dict(
            text=f"Actual vs. Promedio Histórico — Mes {date.today().month} · "
                 f"Zona Peravia | Dr. Johan Tapia, PhD",
            font={"size":11,"color":"#555"}, x=0.5,
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Interpretación cuantitativa rápida
    col_i = st.columns(4)
    for i, am in enumerate(amenazas):
        delta = resultado[am]["score"] - hist_means[am]
        z     = delta / max(hist_std[am], 0.1)
        signo = "▲" if delta > 0 else "▼"
        c     = "#F44336" if delta > 5 else "#4CAF50" if delta < -5 else "#FF9800"
        with col_i[i]:
            st.markdown(
                f'<div style="text-align:center;padding:8px;background:white;'
                f'border-radius:8px;border-top:3px solid {c};">'
                f'<div style="font-size:0.7rem;color:#888;">{AMENAZA_LABEL[am]}</div>'
                f'<div style="font-size:1.1rem;font-weight:800;color:{c};">'
                f'{signo} {abs(delta):.1f}</div>'
                f'<div style="font-size:0.7rem;color:#888;">vs media (Z={z:.1f}σ)</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Bloque 5: Pronóstico ───────────────────────────────────────────────────

def _render_pronostico(predictor, feno_val, mes_actual):
    pronostico = fetch_forecast_week()
    if not pronostico:
        st.warning("Pronóstico no disponible.")
        return

    # Calcular riesgo proyectado por día
    fechas  = [datetime.strptime(d["fecha"],"%Y-%m-%d").strftime("%a %d") for d in pronostico]
    t_max   = [d["temp_max"]      for d in pronostico]
    t_min   = [d["temp_min"]      for d in pronostico]
    lluvia  = [d["precipitacion"] for d in pronostico]
    riesgo_proyectado = []
    for d in pronostico:
        t_med = (d["temp_max"] + d["temp_min"]) / 2
        r = predictor.predict(
            temp=t_med, hum=75.0, lluvia=d["precipitacion"],
            dias_sin_lluvia=0 if d["precipitacion"] > 0.5 else 2,
            fenologia=feno_val, mes=mes_actual,
        )
        riesgo_proyectado.append(max(r[a]["score"] for a in r))

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.08,
                        subplot_titles=("Temperatura Proyectada (°C)",
                                        "Riesgo Global Proyectado"))

    fig.add_trace(go.Scatter(x=fechas, y=t_max, name="T. Máx.",
                             line=dict(color="#E53935",width=2),
                             mode="lines+markers"), row=1, col=1)
    fig.add_trace(go.Scatter(x=fechas, y=t_min, name="T. Mín.",
                             line=dict(color="#1E88E5",width=2),
                             mode="lines+markers"), row=1, col=1)
    fig.add_trace(go.Bar(x=fechas, y=lluvia, name="Lluvia mm",
                         marker_color="rgba(30,136,229,0.3)",
                         yaxis="y3"), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=fechas, y=riesgo_proyectado, name="Riesgo proyectado",
        mode="lines+markers+text",
        text=[f"{r:.0f}" for r in riesgo_proyectado],
        textposition="top center",
        line=dict(color="#F9A825", width=3),
        fill="tozeroy",
        fillcolor="rgba(249,168,37,0.12)",
    ), row=2, col=1)
    fig.add_hrect(y0=50, y1=75, fillcolor="rgba(244,67,54,0.08)",
                  line_width=0, row=2, col=1)
    fig.add_hrect(y0=75, y1=100, fillcolor="rgba(123,31,162,0.08)",
                  line_width=0, row=2, col=1)

    fig.update_layout(
        height=420, plot_bgcolor="#F9FBF9",
        margin=dict(l=20,r=20,t=50,b=20),
        legend=dict(orientation="h", y=-0.08),
        title=dict(
            text="Pronóstico 7 días · Baní (lat=18.28, lon=-70.33) · Open-Meteo",
            font={"size":11,"color":"#888"}, x=0.5,
        ),
    )
    fig.update_yaxes(range=[0,110], row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)


# ── Bloque 6: Interpretación IA ───────────────────────────────────────────

def _render_interpretacion_ia(analisis, resultado, clima, df_hist, predictor):
    color_map = {"Bajo":"#E8F5E9","Moderado":"#FFF8E1",
                 "Elevado":"#FBE9E7","Critico":"#F3E5F5"}
    fg_map    = {"Bajo":"#2E7D32","Moderado":"#F57F17",
                 "Elevado":"#BF360C","Critico":"#4A148C"}
    ng = analisis["nivel_alerta_global"]

    st.markdown(
        f'<div style="background:{color_map[ng]};border-left:6px solid '
        f'{fg_map[ng]};padding:16px 20px;border-radius:10px;margin-bottom:16px;">'
        f'<div style="font-size:0.75rem;font-weight:800;color:{fg_map[ng]};'
        f'text-transform:uppercase;letter-spacing:1px;">Diagnóstico IA — '
        f'Nivel {ng}</div>'
        f'<div style="font-size:0.92rem;color:#333;margin-top:8px;line-height:1.6;">'
        f'{analisis["resumen"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Comparativa estadística
    if df_hist is not None:
        df_p = predictor.predict_batch(df_hist)
        st.markdown("**Análisis estadístico vs. histórico del mismo mes:**")
        col_s = st.columns(4)
        for i, am in enumerate(AMENAZA_LABEL):
            col_name = f"pred_{am}"
            if col_name in df_p.columns:
                hist_m  = df_p[col_name].mean()
                hist_p5 = df_p[col_name].quantile(0.05)
                hist_p95= df_p[col_name].quantile(0.95)
                actual  = resultado[am]["score"]
                pct_rank = float((df_p[col_name] <= actual).mean() * 100)
                c = "#F44336" if pct_rank > 75 else "#FF9800" if pct_rank > 50 else "#4CAF50"
                with col_s[i]:
                    st.markdown(
                        f'<div style="background:white;border-radius:8px;'
                        f'padding:10px;border-left:3px solid {c};">'
                        f'<div style="font-size:0.75rem;font-weight:700;">'
                        f'{AMENAZA_LABEL[am]}</div>'
                        f'<div style="font-size:0.78rem;color:#666;">'
                        f'Actual: <b>{actual:.1f}</b><br>'
                        f'Media hist.: {hist_m:.1f}<br>'
                        f'Rango p5–p95: {hist_p5:.1f}–{hist_p95:.1f}<br>'
                        f'Percentil: <b style="color:{c};">{pct_rank:.0f}°</b></div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    # Plan de acción
    if analisis["plan_accion"]:
        st.markdown("**Plan de acción recomendado:**")
        for paso in analisis["plan_accion"]:
            tag   = paso.split("]")[0].replace("[","")
            texto = paso.split("] ",1)[-1] if "] " in paso else paso
            c_map = {"URGENTE":"#F44336","PREVENTIVO":"#FF9800","MONITOREO":"#4CAF50"}
            c = c_map.get(tag, "#999")
            st.markdown(
                f'<div style="border-left:3px solid {c};padding:7px 12px;'
                f'background:{c}10;border-radius:0 6px 6px 0;margin-bottom:6px;'
                f'font-size:0.87rem;">'
                f'<strong style="color:{c};">{tag}</strong> — {texto}</div>',
                unsafe_allow_html=True,
            )

    st.caption(
        "Interpretación generada por AgroAsistente IA · "
        "Motor: reglas expertas + Random Forest · "
        "Dr. Johan Tapia, PhD | AgroRisk Peravia v3"
    )


# ── Reporte texto completo ─────────────────────────────────────────────────

def _construir_reporte_completo(clima, resultado, feno_label, zona, tecnico,
                                df_hist, analisis) -> str:
    hoy  = date.today().strftime("%d de %B de %Y")
    hora = datetime.now().strftime("%H:%M")
    src  = "API Open-Meteo (en tiempo real)" if clima["source"]!="fallback" else "ONAMET referencia"

    ln = [
        "=" * 65,
        "   REPORTE EJECUTIVO FITOSANITARIO — MANGO",
        "   Sistema AgroRisk Peravia v3 · Modelo Random Forest",
        "=" * 65,
        "",
        f"  Preparado por : {tecnico}",
        f"  Institución   : Ministerio de Agricultura, RD",
        f"  Zona          : {zona}",
        f"  Fecha         : {hoy}  |  Hora: {hora}",
        f"  Fenología     : {feno_label}",
        f"  Fuente clima  : {src}",
        "",
        "─" * 65,
        "  I. CONDICIONES CLIMÁTICAS",
        "─" * 65,
        f"  Temperatura máx/mín/media : {clima['temp_max']} / {clima['temp_min']} / {clima['temp_media']} °C",
        f"  Humedad relativa          : {clima['humedad']} %",
        f"  Precipitación             : {clima['precipitacion']} mm",
        "",
        "─" * 65,
        "  II. ÍNDICES DE RIESGO FITOSANITARIO",
        "─" * 65,
    ]
    for am, lbl in AMENAZA_LABEL.items():
        d   = resultado[am]
        tag = NIVEL_TAG.get(d["nivel"],"")
        ln.append(f"  {lbl:<46} [{tag}]  {d['score']:>5.1f}/100")

    ln += ["", "─"*65, "  III. DIAGNÓSTICO IA", "─"*65]
    if analisis:
        ln.append(f"  Nivel de alerta global: {analisis['nivel_alerta_global'].upper()}")
        ln.append("")
        # Wrap the summary text
        import textwrap
        for line in textwrap.wrap(analisis["resumen"], 62):
            ln.append(f"  {line}")
        ln.append("")
        ln += ["─"*65, "  IV. PLAN DE ACCIÓN PRIORITARIO", "─"*65]
        for paso in analisis["plan_accion"]:
            ln.append(f"  {paso}")

    if df_hist is not None:
        ln += ["", "─"*65, "  V. CONTEXTO HISTÓRICO (mes actual)", "─"*65]
        ln.append("  [Comparativa con datos 2022–2024 generada en dashboard]")

    ln += [
        "",
        "─" * 65,
        "  VI. RECOMENDACIONES TÉCNICAS",
        "─" * 65,
    ]
    for am, lbl in AMENAZA_LABEL.items():
        d = resultado[am]
        if d["nivel"] in ("Medio","Alto","Critico"):
            nombre = lbl.split("(")[0].strip()
            ln += ["", f"  [{nombre}] — {d['nivel']} ({d['score']:.1f}/100)",
                   f"  {d['recomendacion']}"]

    ln += [
        "",
        "=" * 65,
        "  Generado: Sistema AgroRisk Peravia v3",
        "  Motor predictivo: Random Forest · 4 amenazas · 1,096 dias",
        "  Datos climáticos: Open-Meteo / ONAMET",
        "  Autor del sistema: Dr. Johan Tapia, PhD",
        "  Ministerio de Agricultura · Unidad de Sanidad Vegetal",
        "  NOTA: Reporte orientativo. Confirmar diagnóstico en campo.",
        "=" * 65,
    ]
    return "\n".join(ln)


# ── Helpers ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def _cargar_hist_mes(mes: int):
    if not CSV_PATH.exists():
        return None
    try:
        df = pd.read_csv(CSV_PATH, parse_dates=["fecha"])
        return df[df["fecha"].dt.month == mes].copy()
    except Exception:
        return None
