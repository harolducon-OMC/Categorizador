# -*- coding: utf-8 -*-
"""
core/state.py
Estado compartido entre páginas (st.session_state), secretos y carga de datos.
"""

import os
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

from core.llm import DEFAULT_MODEL, DEFAULT_PROVIDER, LLM, PROVIDER_CONFIG

DEFAULTS = {
    "df": None,            # DataFrame cargado
    "df_sig": None,        # firma del archivo/hoja cargados
    "df_name": "",
    "codeframes": {},      # pregunta -> DataFrame (propuesta de categorías)
    "coded": {},           # pregunta -> {"kind", "labels", "categories", ...}
    "brand_raw": {},       # pregunta -> menciones crudas por fila
    "insights": {},        # pregunta -> resultado de insights
    "validation": {},      # pregunta -> resultados de segunda opinión
    "api_key_input": "",
    "ai_provider": DEFAULT_PROVIDER,
}


def init() -> None:
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, dict) else value


def get_secret(name: str, default=None):
    try:
        return st.secrets[name]
    except Exception:  # sin secrets.toml o clave inexistente
        return os.environ.get(name, default)


# ----------------------------------------------------------------------- datos
def read_table(uploaded_file, sheet: Optional[str] = None) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        for enc in ("utf-8-sig", "latin-1"):
            try:
                uploaded_file.seek(0)
                return pd.read_csv(uploaded_file, sep=None, engine="python", encoding=enc)
            except UnicodeDecodeError:
                continue
        raise ValueError("No se pudo leer el CSV (codificación no reconocida).")
    uploaded_file.seek(0)
    return pd.read_excel(uploaded_file, sheet_name=sheet or 0, engine="openpyxl")


def set_data(df: pd.DataFrame, name: str, sig: str) -> None:
    """Guarda el dataset y reinicia todo lo derivado de uno anterior."""
    st.session_state.df = df
    st.session_state.df_name = name
    st.session_state.df_sig = sig
    st.session_state.pop("categorization_export_bytes", None)
    st.session_state.pop("report_bytes", None)
    for key in ("codeframes", "coded", "brand_raw", "insights", "validation"):
        st.session_state[key] = {}
    for key in list(st.session_state.keys()):
        if str(key).startswith(("cf::", "bm::", "open_questions")):
            del st.session_state[key]


def require_data() -> pd.DataFrame:
    df = st.session_state.get("df")
    if df is None:
        st.info("Primero carga tu archivo en la página de inicio.")
        st.page_link("Home.py", label="Ir a Carga de datos", icon="📂")
        st.stop()
    return df


# ------------------------------------------------------------------------- LLM
@st.cache_resource(show_spinner=False)
def _build_llm(api_key: str, fast: str, smart: str, provider: str) -> LLM:
    return LLM(api_key, fast=fast, smart=smart, provider=provider)


def get_llm() -> Optional[LLM]:
    provider = st.session_state.get("ai_provider", DEFAULT_PROVIDER)
    if provider not in PROVIDER_CONFIG:
        provider = DEFAULT_PROVIDER
    env_name = PROVIDER_CONFIG[provider]["key_env"]
    key = get_secret(env_name)
    if provider == "gemini":
        key = key or get_secret("GOOGLE_API_KEY")
    key = key or st.session_state.get(f"api_key_input::{provider}") or st.session_state.get("api_key_input") or ""
    if not key:
        return None
    configured_default = PROVIDER_CONFIG[provider].get("default_model") or DEFAULT_MODEL
    legacy_model = get_secret("MODEL_FAST", configured_default) if provider == "anthropic" else configured_default
    custom_choice = st.session_state.get(f"ai_model_choice::{provider}") == "__custom_model__"
    selected_model = st.session_state.get(f"ai_model::{provider}") or legacy_model
    custom_model = st.session_state.get(f"ai_model_custom::{provider}") if custom_choice else ""
    if custom_choice and not (custom_model and custom_model.strip()):
        return None
    model = custom_model.strip() if custom_model and custom_model.strip() else selected_model
    if not model:
        return None
    smart_model = get_secret("MODEL_SMART", model) if provider == "anthropic" and not custom_choice else model
    return _build_llm(key, model, smart_model, provider)


# ------------------------------------------------------------ marcas -> awareness
def collect_brand_info() -> Optional[Dict]:
    """Une entidades y alias de todas las preguntas de marcas ya aplicadas."""
    entities: List[str] = []
    aliases: Dict[str, set] = {}
    questions: List[str] = []
    for q, info in st.session_state.get("coded", {}).items():
        if info.get("kind") != "marcas":
            continue
        questions.append(q)
        for e in info.get("entities", []):
            if e not in entities:
                entities.append(e)
            aliases.setdefault(e, set()).update(info.get("aliases", {}).get(e, []))
    if not entities:
        return None
    return {"entities": entities, "aliases": {e: sorted(a) for e, a in aliases.items()}, "questions": questions}
