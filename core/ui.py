# -*- coding: utf-8 -*-
"""Interfaz compartida, autenticación opcional y tema de gráficas."""
import base64
import hmac
from functools import lru_cache
from pathlib import Path

import streamlit as st

from core import state
from core.llm import DEFAULT_PROVIDER, PROVIDER_CONFIG

ROOT = Path(__file__).resolve().parent.parent
BG_PATH = ROOT / "assets" / "Background.jpeg"
LOGO_PATH = ROOT / "assets" / "omnicom_media_group_latam_logo_Low_Res.jpg"
APP_NAME = "Plataforma de Insights"
COLORWAY = ["#2563EB", "#0F766E", "#D97706", "#DB2777", "#7C3AED", "#0891B2", "#EA580C", "#64748B"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root { color-scheme:light; }
html, body, [class*="st-"], .stApp { font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.stApp { background:#F3F6FA __BG__; background-size:cover; background-position:center; background-attachment:fixed; }
[data-testid="stAppViewContainer"] { background:rgba(244,247,251,.96); }
[data-testid="stHeader"] { background:rgba(244,247,251,.94); }
.block-container { max-width:1320px; padding:2.2rem clamp(1.1rem,4vw,3.5rem) 4rem !important; }
[data-testid="stSidebar"] { background:#101B32; border-right:1px solid #263654; color:#E8EEF8; }

/* Navegación nativa: Streamlit puede aplicar colores más específicos a los enlaces. */
[data-testid="stSidebarNav"] a,
[data-testid="stSidebarNav"] a *,
[data-testid="stSidebarNav"] [role="listitem"] * {
  color:#E8EEF8 !important;
  -webkit-text-fill-color:#E8EEF8 !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
  background:rgba(148,163,184,.26) !important;
  border-radius:8px !important;
}
[data-testid="stSidebarNav"] a:hover { background:rgba(148,163,184,.16) !important; }

/* Etiquetas/captions legibles, manteniendo los campos de entrada oscuros sobre blanco. */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
  color:#E8EEF8 !important;
  -webkit-text-fill-color:#E8EEF8 !important;
}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
  color:#B5C2D6 !important;
  -webkit-text-fill-color:#B5C2D6 !important;
}
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stTextArea textarea,
[data-testid="stSidebar"] div[data-baseweb="select"] > div {
  background:#fff !important;
  color:#17243A !important;
  -webkit-text-fill-color:#17243A !important;
}
[data-testid="stSidebar"] div[data-baseweb="select"] *,
[data-testid="stSidebar"] div[data-baseweb="popover"] li * {
  color:#17243A !important;
  -webkit-text-fill-color:#17243A !important;
}

/* Tipografía general */
[data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] label, [data-testid="stAppViewContainer"] h1,
[data-testid="stAppViewContainer"] h2, [data-testid="stAppViewContainer"] h3,
[data-testid="stAppViewContainer"] h4, [data-testid="stAppViewContainer"] h5,
[data-testid="stAppViewContainer"] h6, [data-testid="stAppViewContainer"] li { color:#17243A; }
h1 { font-size:clamp(2rem,4vw,2.65rem) !important; letter-spacing:-.045em !important; line-height:1.14 !important; font-weight:750 !important; margin-bottom:.35rem !important; }
h2 { font-size:1.55rem !important; letter-spacing:-.025em !important; font-weight:700 !important; }
h3 { font-size:1.22rem !important; font-weight:650 !important; }
[data-testid="stCaptionContainer"] { color:#64748B !important; }
[data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] p { line-height:1.6; }

/* Métricas, tarjetas y acordeón */
[data-testid="stMetric"] { background:#fff; border:1px solid #E1E7F0; border-radius:14px; padding:1rem 1.15rem; box-shadow:0 3px 12px rgba(23,36,58,.045); }
[data-testid="stMetricLabel"] { color:#64748B !important; font-weight:550; }
[data-testid="stMetricValue"] { color:#17243A !important; font-weight:700; }
[data-testid="stExpander"] { background:#fff; border:1px solid #DCE4EE; border-radius:12px; overflow:hidden; }
[data-testid="stExpander"] summary { padding:.85rem 1rem; }
[data-testid="stExpander"] summary p { color:#24344D !important; font-weight:600; line-height:1.45 !important; }
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] li { color:#334155 !important; line-height:1.65 !important; }
[data-testid="stAlert"] { border-radius:11px; }

/* Cargador nativo: conservar su funcionalidad y dar prioridad a contraste y foco. */
.stFileUploader { margin-top:.7rem; }
.stFileUploader [data-testid="stFileUploaderDropzone"],
.stFileUploader section { background:#F8FAFC !important; border:1.5px dashed #9AAAC0 !important; border-radius:12px !important; padding:1.15rem 1rem !important; }
.stFileUploader [data-testid="stFileUploaderDropzone"] *,
.stFileUploader section span, .stFileUploader section small,
.stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] * { color:#475569 !important; -webkit-text-fill-color:#475569 !important; opacity:1 !important; }
.stFileUploader button { color:#fff !important; -webkit-text-fill-color:#fff !important; background:#1D4ED8 !important; border:1px solid #1D4ED8 !important; border-radius:8px !important; min-height:2.5rem !important; padding:.35rem 1rem !important; font-weight:650 !important; box-shadow:0 2px 4px rgba(29,78,216,.16); }
.stFileUploader button *, .stFileUploader button span { color:#fff !important; -webkit-text-fill-color:#fff !important; opacity:1 !important; }
.stFileUploader button:hover { background:#1E40AF !important; border-color:#1E40AF !important; }
.stFileUploader button:focus-visible { outline:3px solid #93C5FD !important; outline-offset:2px !important; }

/* Entradas */
.stTextInput input,.stTextArea textarea,.stNumberInput input,
div[data-baseweb="select"] > div { background:#fff !important; color:#17243A !important; -webkit-text-fill-color:#17243A !important; border:1px solid #CBD5E1 !important; border-radius:8px !important; }
.stTextInput input::placeholder,.stTextArea textarea::placeholder { color:#718096 !important; -webkit-text-fill-color:#718096 !important; }
div[data-baseweb="select"] *,div[data-baseweb="popover"] li,div[data-baseweb="popover"] li * { color:#17243A !important; -webkit-text-fill-color:#17243A !important; }
span[data-baseweb="tag"] { background:#1D4ED8 !important; }
span[data-baseweb="tag"] * { color:#fff !important; -webkit-text-fill-color:#fff !important; }

/* Acciones y tabs */
.stButton > button, .stDownloadButton > button { border-radius:9px !important; font-weight:600 !important; min-height:2.55rem; }
.stButton > button[kind="primary"],.stDownloadButton > button { background:#1D4ED8 !important; color:#fff !important; border:1px solid #1D4ED8 !important; }
.stButton > button[kind="primary"] *, .stDownloadButton > button * { color:#fff !important; }
.stButton > button:hover,.stDownloadButton > button:hover { filter:brightness(.94); }
button[data-baseweb="tab"] { min-height:2.8rem; }
button[data-baseweb="tab"] p { color:#475569 !important; font-weight:600; white-space:normal; line-height:1.35 !important; }
button[data-baseweb="tab"][aria-selected="true"] p { color:#1D4ED8 !important; }
[data-testid="stDataFrame"], [data-testid="stTable"] { border:1px solid #E1E7F0; border-radius:10px; overflow:hidden; }
.insights-footer { position:fixed; left:0; right:0; bottom:0; z-index:999999; display:flex; justify-content:space-between; align-items:center; gap:1rem; padding:.65rem clamp(1rem,4vw,3.5rem); background:rgba(16,27,50,.96); color:#E8EEF8; font-size:.82rem; border-top:1px solid rgba(255,255,255,.14); box-shadow:0 -4px 18px rgba(15,23,42,.12); }
.insights-footer span { color:#E8EEF8 !important; -webkit-text-fill-color:#E8EEF8 !important; }
@media(max-width:700px) { .block-container { padding:1.3rem .9rem 2rem !important; } h1 { font-size:1.9rem !important; } }
@media(max-width:460px) { .insights-footer { font-size:.72rem; padding:.6rem .75rem; } }
</style>
"""


@lru_cache(maxsize=1)
def _background_css() -> str:
    if BG_PATH.exists():
        encoded = base64.b64encode(BG_PATH.read_bytes()).decode()
        return f"url('data:image/jpeg;base64,{encoded}')"
    return "#F3F6FA"


def setup_page(title: str, icon: str = "📊") -> None:
    """Debe ser lo primero que ejecuta cada página (set_page_config + estilos)."""
    st.set_page_config(
        page_title=f"{title} · {APP_NAME}",
        page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else icon,
        layout="wide",
    )
    state.init()
    st.markdown(CSS.replace("__BG__", _background_css()), unsafe_allow_html=True)
    st.markdown(
        '<div class="insights-footer"><span>Creado por el equipo Research</span>'
        '<span>© Harold Ducon</span></div>',
        unsafe_allow_html=True,
    )


def require_login() -> None:
    """Exige un usuario y una contraseña configurados en Streamlit Secrets."""
    username = state.get_secret("APP_USERNAME")
    password = state.get_secret("APP_PASSWORD")
    if not username or not password:
        st.title(APP_NAME)
        st.error(
            "Acceso no configurado. Para usar la app, define APP_USERNAME y APP_PASSWORD "
            "en .streamlit/secrets.toml o en Streamlit Cloud → Settings → Secrets."
        )
        st.stop()
    if st.session_state.get("_auth"):
        return
    st.title(APP_NAME)
    with st.form("login_form"):
        entered_username = st.text_input("Usuario", key="_login_username")
        entered_password = st.text_input("Contraseña", type="password", key="_login_password")
        submitted = st.form_submit_button("Entrar", type="primary")
    if submitted:
        valid_username = hmac.compare_digest(entered_username.encode("utf-8"), str(username).encode("utf-8"))
        valid_password = hmac.compare_digest(entered_password.encode("utf-8"), str(password).encode("utf-8"))
        if valid_username and valid_password:
            st.session_state["_auth"] = True
            st.rerun()
        st.error("Usuario o contraseña incorrectos.")
    st.stop()


def header(title: str, subtitle: str = "") -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def sidebar() -> None:
    with st.sidebar:
        st.header(APP_NAME)
        df = st.session_state.get("df")
        if df is None:
            st.caption("📂 Sin datos cargados")
        else:
            st.caption(f"📂 {st.session_state.df_name} · {len(df):,} filas × {df.shape[1]} columnas")

        st.markdown("**Proveedor y modelo de IA**")
        provider_ids = list(PROVIDER_CONFIG)
        if st.session_state.get("ai_provider") not in provider_ids:
            st.session_state["ai_provider"] = DEFAULT_PROVIDER
        provider = st.selectbox(
            "Proveedor", provider_ids,
            format_func=lambda pid: PROVIDER_CONFIG[pid]["name"],
            key="ai_provider",
        )
        config = PROVIDER_CONFIG[provider]
        provider_secret = state.get_secret(config["key_env"])
        if not provider_secret and provider == "gemini":
            provider_secret = state.get_secret("GOOGLE_API_KEY")
        if provider_secret:
            st.caption("API key cargada de Secrets; permanece oculta.")
        else:
            st.text_input(
                "API key (solo esta sesión)", type="password",
                key=f"api_key_input::{provider}",
                help="La clave se usa desde el servidor. No la compartas en el chat ni la subas a GitHub.",
            )
        active_key = provider_secret or st.session_state.get(f"api_key_input::{provider}") or ""

        model_options = list(config.get("models", []))
        custom_option = "__custom_model__"
        choices = model_options + [custom_option]
        selected_model = st.session_state.get(f"ai_model::{provider}")
        default_model = selected_model if selected_model in model_options else (config.get("default_model") or custom_option)
        selected_index = choices.index(default_model) if default_model in choices else len(choices) - 1
        widget_key = f"ai_model_choice::{provider}"
        if st.session_state.get(widget_key) not in choices:
            st.session_state[widget_key] = default_model

        def model_label(model: str) -> str:
            if model == custom_option:
                return "Escribir ID de otro modelo…"
            if provider == "openrouter":
                return f"{model} · gratis"
            if provider in ("gemini", "groq", "cohere"):
                return f"{model} · gratis con límites"
            return model

        choice = st.selectbox(
            "Modelo", choices, index=selected_index,
            format_func=model_label, key=widget_key,
        )
        if choice == custom_option:
            custom_value = st.text_input(
                "ID del modelo", key=f"ai_model_custom::{provider}",
                placeholder="Pega el ID exacto que muestra tu proveedor",
            )
            if custom_value and provider in ("gemini", "cohere", "anthropic"):
                st.warning("Un modelo personalizado puede tener precio o límites distintos a las opciones sugeridas; verifica su ficha antes de usarlo.")
            if custom_value and provider == "openrouter" and not custom_value.endswith(":free"):
                st.warning("Este ID no termina en :free y podría generar cargos. Elige un modelo gratuito si no deseas pagar.")
        else:
            st.session_state[f"ai_model::{provider}"] = choice
        st.caption(config["free_note"])

        has_key = bool(active_key)
        model_ready = choice != custom_option or bool(st.session_state.get(f"ai_model_custom::{provider}", "").strip())
        if has_key and model_ready:
            if st.button("Probar conexión IA", key="test_llm_connection"):
                try:
                    client = state.get_llm()
                    if client is None:
                        st.error("No se encontró la clave para el proveedor elegido.")
                    else:
                        client.text("Responde únicamente OK.", "Prueba de conexión", max_tokens=12)
                        st.success(f"Conexión correcta con {config['name']}.")
                except Exception as exc:
                    st.error(str(exc))

        st.caption(f"{len(st.session_state.get('coded', {}))} pregunta(s) categorizada(s)")


def style_fig(fig, height: int = 460):
    """Tema claro legible para dashboards profesionales."""
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif", color="#24344D", size=13),
        colorway=COLORWAY,
        height=height,
        margin=dict(l=10, r=20, t=50, b=10),
        legend=dict(bgcolor="rgba(255,255,255,.7)"),
    )
    fig.update_xaxes(gridcolor="#E2E8F0")
    fig.update_yaxes(gridcolor="#E2E8F0")
    return fig
