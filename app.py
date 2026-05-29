"""
AgroRisk Peravia v2 — Entry point Streamlit.
Sistema de prediccion fitosanitaria · Mango · Zona Peravia, Bani RD.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from datetime import date

st.set_page_config(
    page_title="AgroRisk Peravia",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS global ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Ocultar nav automática de páginas de Streamlit */
    [data-testid="stSidebarNavItems"]    { display: none !important; }
    [data-testid="stSidebarNavSeparator"]{ display: none !important; }
    section[data-testid="stSidebarNav"]  { display: none !important; }

    /* App background */
    .stApp { background-color: #F9FBF9; }

    /* Sidebar verde institucional */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1B5E20 0%, #2E7D32 100%);
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] span:not([data-baseweb]) {
        color: #E8F5E9 !important;
    }
    /* Radio buttons del sidebar */
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        color: white !important;
        font-size: 0.95rem !important;
        font-weight: 500 !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
        gap: 4px;
    }

    /* Títulos */
    h1 { color: #1B5E20 !important; font-weight: 800 !important; }
    h2 { color: #1B5E20 !important; }
    h3 { color: #2E7D32 !important; }

    /* Botones */
    .stButton > button {
        background-color: #1B5E20 !important;
        color: white !important;
        border-radius: 6px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 8px 20px !important;
        transition: background 0.2s;
    }
    .stButton > button:hover {
        background-color: #F9A825 !important;
        color: #1B5E20 !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #1B5E20 !important;
    }

    /* Métricas */
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 700 !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background: #EEF4EE !important;
        border-radius: 6px !important;
        color: #1B5E20 !important;
        font-weight: 600 !important;
        padding: 6px 16px !important;
    }
    .stTabs [aria-selected="true"] {
        background: #1B5E20 !important;
        color: white !important;
    }

    /* Footer */
    .footer-bar {
        background: #1B5E20;
        color: #ccc;
        text-align: center;
        padding: 10px;
        font-size: 0.78rem;
        border-radius: 8px;
        margin-top: 30px;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-thumb { background: #2E7D32; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ── Predictor cacheado ─────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Entrenando modelos de prediccion (primera vez)...")
def _load_predictor():
    from core.predictor import AgroRiskPredictor
    from core.data_generator import generate_historical
    import pandas as pd

    csv_path = ROOT / "data" / "peravia_historico.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    if csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["fecha"])
    else:
        df = generate_historical()
        df.to_csv(csv_path, index=False)

    predictor = AgroRiskPredictor()
    predictor.train(df)
    return predictor


predictor = _load_predictor()

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='text-align:center;padding:10px 0 4px;'>"
        "<div style='font-size:1.6rem;font-weight:900;letter-spacing:1px;"
        "color:white;'>AgroRisk</div>"
        "<div style='font-size:0.85rem;color:#FDD835;font-weight:600;'>"
        "Peravia · Bani, RD</div>"
        "<div style='font-size:0.78rem;color:#A5D6A7;margin-top:2px;'>"
        f"{date.today().strftime('%d/%m/%Y')}</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<hr style='border-color:rgba(255,255,255,0.2);margin:10px 0;'>",
        unsafe_allow_html=True,
    )

    pagina = st.radio(
        "Navegacion",
        ["Dashboard", "Simulador", "Historico", "Reporte del Dia", "Asistente IA", "Mapa"],
        label_visibility="collapsed",
    )

    st.markdown(
        "<hr style='border-color:rgba(255,255,255,0.2);margin:12px 0;'>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-size:0.72rem;color:#A5D6A7;line-height:1.8;'>"
        "Ministerio de Agricultura<br>"
        "Republica Dominicana<br>"
        "Unidad de Sanidad Vegetal<br><br>"
        "<span style='color:#FDD835;'>Modelo AgroRisk v3.0</span><br>"
        "Motor: Random Forest<br>"
        "Datos: Open-Meteo / ONAMET<br><br>"
        "<span style='color:#FDD835;font-weight:700;'>Dr. Johan Tapia, PhD</span><br>"
        "<span style='color:#C8E6C9;font-size:0.68rem;'>Autor & Desarrollador</span>"
        "</div>",
        unsafe_allow_html=True,
    )

# ── Enrutador ──────────────────────────────────────────────────────────────
if pagina == "Dashboard":
    from pages._01_dashboard import render
    render(predictor)

elif pagina == "Simulador":
    from pages._02_simulador import render
    render(predictor)

elif pagina == "Historico":
    from pages._03_historico import render
    render(predictor)

elif pagina == "Reporte del Dia":
    from pages._04_reporte import render
    render(predictor)

elif pagina == "Asistente IA":
    from pages._05_asistente import render
    render(predictor)

elif pagina == "Mapa":
    from pages._06_mapa import render
    render(predictor)
