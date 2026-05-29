"""
Asistente IA Agronomico — AgroRisk Peravia.
Chat contextual con el estado fitosanitario actual.
"""
from __future__ import annotations

from datetime import date

import streamlit as st

from core.asistente_ia import AgroAsistente, _nombre
from core.climate_api import fetch_today
from core.data_generator import FENOLOGIA_LABELS, FENOLOGIA_MAP
from core.predictor import AgroRiskPredictor

SUGERENCIAS_RAPIDAS = [
    "Que debo hacer hoy?",
    "Como esta el riesgo de mosca?",
    "Que es la antracnosis?",
    "Que condiciones favorecen los trips?",
    "Como funciona el modelo de prediccion?",
    "Como esta el clima hoy?",
    "Explica el riesgo de oidio",
    "Estado general de la parcela",
]

COLOR_ALERTA = {
    "Bajo":     ("#E8F5E9", "#2E7D32", "#4CAF50"),
    "Moderado": ("#FFF8E1", "#F57F17", "#FFC107"),
    "Elevado":  ("#FBE9E7", "#BF360C", "#FF5722"),
    "Critico":  ("#F3E5F5", "#4A148C", "#9C27B0"),
}


def render(predictor: AgroRiskPredictor) -> None:
    st.markdown("## Asistente Agronomico IA")
    st.markdown(
        "Consulte al asistente sobre el estado fitosanitario de su parcela, "
        "las amenazas activas y las acciones recomendadas para hoy."
    )
    st.markdown("---")

    # ── Obtener estado actual ──────────────────────────────────────
    clima = fetch_today()
    mes   = date.today().month
    feno_idx = _mes_a_feno_idx(mes)

    resultados = predictor.predict(
        temp=clima["temp_media"],
        hum=clima["humedad"],
        lluvia=clima["precipitacion"],
        dias_sin_lluvia=0 if clima["precipitacion"] > 0.5 else 3,
        fenologia=feno_idx,
        mes=mes,
    )

    asistente = AgroAsistente()
    analisis  = asistente.analizar(resultados, clima, feno_idx, mes)

    # ── Panel de estado ────────────────────────────────────────────
    nivel_g = analisis["nivel_alerta_global"]
    bg, fg, accent = COLOR_ALERTA.get(nivel_g, ("#fff", "#000", "#999"))

    st.markdown(
        f'<div style="background:{bg};border-left:6px solid {accent};'
        f'padding:16px 20px;border-radius:10px;margin-bottom:20px;">'
        f'<div style="font-size:0.8rem;color:{fg};font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1px;">Estado Global de Alerta</div>'
        f'<div style="font-size:2rem;font-weight:800;color:{fg};">{nivel_g.upper()}</div>'
        f'<div style="font-size:0.9rem;color:#555;margin-top:6px;">{analisis["resumen"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Minibadges por amenaza ─────────────────────────────────────
    cols = st.columns(4)
    colores_nivel = {
        "Bajo":    "#4CAF50",
        "Medio":   "#FF9800",
        "Alto":    "#F44336",
        "Critico": "#7B1FA2",
    }
    for i, (amenaza, d) in enumerate(resultados.items()):
        with cols[i]:
            c = colores_nivel[d["nivel"]]
            st.markdown(
                f'<div style="text-align:center;padding:10px;background:white;'
                f'border-radius:10px;border-top:4px solid {c};box-shadow:0 2px 6px rgba(0,0,0,0.07);">'
                f'<div style="font-size:0.75rem;color:#888;">{_nombre(amenaza)}</div>'
                f'<div style="font-size:1.6rem;font-weight:800;color:{c};">{d["score"]:.0f}</div>'
                f'<div style="font-size:0.7rem;color:{c};font-weight:600;">{d["nivel"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Sinergias detectadas ───────────────────────────────────────
    if analisis["sinergias"]:
        st.markdown("#### Interacciones entre Amenazas Detectadas")
        for s in analisis["sinergias"]:
            st.warning(s)

    # ── Alertas estacionales ───────────────────────────────────────
    if analisis["alertas_estacionales"]:
        st.markdown("#### Alertas Estacionales del Mes")
        for a in analisis["alertas_estacionales"]:
            st.info(a)

    # ── Plan de acción priorizado ──────────────────────────────────
    st.markdown("#### Plan de Accion Priorizado")
    for paso in analisis["plan_accion"]:
        if paso.startswith("[URGENTE]"):
            st.markdown(
                f'<div style="background:#FFEBEE;border-left:4px solid #F44336;'
                f'padding:10px 14px;border-radius:6px;margin-bottom:8px;font-size:0.9rem;">'
                f'<strong style="color:#C62828;">URGENTE</strong> — '
                f'{paso.replace("[URGENTE] ", "")}'
                f'</div>',
                unsafe_allow_html=True,
            )
        elif paso.startswith("[PREVENTIVO]"):
            st.markdown(
                f'<div style="background:#FFF3E0;border-left:4px solid #FF9800;'
                f'padding:10px 14px;border-radius:6px;margin-bottom:8px;font-size:0.9rem;">'
                f'<strong style="color:#E65100;">PREVENTIVO</strong> — '
                f'{paso.replace("[PREVENTIVO] ", "")}'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="background:#F9FBF9;border-left:4px solid #4CAF50;'
                f'padding:10px 14px;border-radius:6px;margin-bottom:8px;font-size:0.9rem;">'
                f'<strong style="color:#2E7D32;">MONITOREO</strong> — '
                f'{paso.replace("[MONITOREO] ", "")}'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Interfaz de chat ───────────────────────────────────────────
    st.markdown("#### Consulta al Asistente")

    # Inicializar historial de chat
    if "chat_msgs" not in st.session_state:
        st.session_state.chat_msgs = [
            {
                "rol": "asistente",
                "texto": (
                    "Buenos dias. Soy el Asistente Agronomico AgroRisk. "
                    f"He analizado el estado actual de su parcela y el nivel de alerta es **{nivel_g}**. "
                    "Puede preguntarme sobre cualquier amenaza, condicion climatica o accion a tomar."
                ),
            }
        ]

    # Mostrar historial
    _render_chat(st.session_state.chat_msgs)

    # Sugerencias rapidas
    st.markdown("**Consultas frecuentes:**")
    cols_s = st.columns(4)
    for i, sug in enumerate(SUGERENCIAS_RAPIDAS):
        with cols_s[i % 4]:
            if st.button(sug, key=f"sug_{i}", use_container_width=True):
                _procesar_mensaje(sug, asistente, resultados, clima)
                st.rerun()

    # Input libre
    with st.form("chat_form", clear_on_submit=True):
        col_in, col_btn = st.columns([5, 1])
        with col_in:
            user_input = st.text_input(
                "Escriba su consulta...",
                placeholder="Ej: Que fungicida aplicar para antracnosis?",
                label_visibility="collapsed",
            )
        with col_btn:
            enviado = st.form_submit_button("Enviar", use_container_width=True)

    if enviado and user_input.strip():
        _procesar_mensaje(user_input.strip(), asistente, resultados, clima)
        st.rerun()

    # Botón limpiar
    if len(st.session_state.chat_msgs) > 1:
        if st.button("Limpiar conversacion"):
            st.session_state.chat_msgs = []
            st.rerun()


# ── Helpers ────────────────────────────────────────────────────────────────

def _procesar_mensaje(
    texto: str,
    asistente: AgroAsistente,
    resultados: dict,
    clima: dict,
) -> None:
    st.session_state.chat_msgs.append({"rol": "usuario", "texto": texto})
    respuesta = asistente.responder(texto, resultados, clima)
    st.session_state.chat_msgs.append({"rol": "asistente", "texto": respuesta})


def _render_chat(msgs: list[dict]) -> None:
    for msg in msgs:
        if msg["rol"] == "usuario":
            st.markdown(
                f'<div style="display:flex;justify-content:flex-end;margin:8px 0;">'
                f'<div style="background:#1B5E20;color:white;padding:10px 16px;'
                f'border-radius:18px 18px 4px 18px;max-width:70%;font-size:0.9rem;">'
                f'{msg["texto"]}'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="display:flex;align-items:flex-start;gap:10px;margin:8px 0;">'
                f'<div style="background:#F9A825;color:white;border-radius:50%;'
                f'width:32px;height:32px;display:flex;align-items:center;justify-content:center;'
                f'font-weight:800;font-size:0.85rem;flex-shrink:0;">IA</div>'
                f'<div style="background:#EEF4EE;color:#1A1A1A;padding:10px 16px;'
                f'border-radius:4px 18px 18px 18px;max-width:80%;font-size:0.88rem;line-height:1.5;">'
                f'{msg["texto"].replace(chr(10), "<br>")}'
                f'</div></div>',
                unsafe_allow_html=True,
            )
    # Espaciado final
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)


def _mes_a_feno_idx(mes: int) -> int:
    _map = {1: 2, 2: 2, 3: 3, 4: 3, 5: 3, 6: 4, 7: 4, 8: 4, 9: 4, 10: 0, 11: 0, 12: 1}
    return _map.get(mes, 0)
