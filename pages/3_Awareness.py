# -*- coding: utf-8 -*-
"""Awareness / Recordación (TOM, Espontáneo, Ayudado) con la lógica del proyecto original."""

import json

import pandas as pd
import plotly.express as px
import streamlit as st

from core import awareness as aw
from core import state, ui

ui.setup_page("Awareness", "🎯")
ui.require_login()
ui.sidebar()

# Inyección de CSS estricto para limpiar formularios, textareas, botones e íconos defectuosos
st.markdown("""
<style>
    /* Oculta textos o íconos defectuosos de desplegables y tooltips */
    [data-testid="stSidebar"] [title], 
    [data-testid="stSidebarNav"] [title],
    .stSidebar [title],
    .streamlit-expanderHeader span {
        display: none !important;
    }

    /* Campos claros con texto oscuro para conservar contraste en la página clara. */
    .stTextArea textarea, .stTextInput input {
        background-color: #FFFFFF !important;
        color: #17243A !important;
        -webkit-text-fill-color: #17243A !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #4A90E2 !important;
        box-shadow: 0 0 0 1px #4A90E2 !important;
    }

    /* Estilizado limpio para tarjetas/contenedores */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] {
        border-radius: 10px;
    }

    /* Estilizado elegante para bloques de métricas */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 12px 18px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

ui.header("Awareness / Recordación", "TOM, espontáneo y ayudado por marca y segmento.")

df = state.require_data()
brand_info = state.collect_brand_info()

modes = ["Bancos", "Conglomerados Financieros", "Personalizado"]
if brand_info:
    modes.append("Marcas detectadas (Categorización)")

st.subheader("Tipo de estudio")
mode = st.radio("Selecciona el tipo de estudio", modes, index=len(modes) - 1 if brand_info else 2, horizontal=True, label_visibility="collapsed")

# ------------------------------------------------------------------ defaults
if mode == "Bancos":
    d_ent, d_ali, d_nor = aw.BANKS, aw.BANK_ALIASES, aw.BANK_NORMALIZATIONS
    d_demo = ("F1 ", "F2 ", "F4 ", "F3 ", "0")
    t1 = ("AWA PUB", "0", "0", "0")
    t2 = ("AWA Marca", "P1", "P1A.1\nP1A.2\nP1A.3", "P2.1\nP2.2\nP2.3")
elif mode == "Conglomerados Financieros":
    d_ent, d_ali, d_nor = aw.CONGLOMERATES, aw.CONGLOMERATE_ALIASES, aw.CONGLOMERATE_NORMALIZATIONS
    d_demo = ("F1", "F2a", "F4", "F3", "F5")
    t1 = ("Desactivado", "0", "0", "0")
    t2 = ("Conglomerados AWA", "P1 -", "P1A -", "P2-P2.")
elif mode.startswith("Marcas detectadas"):
    d_ent, d_ali, d_nor = brand_info["entities"], brand_info["aliases"], []
    d_demo = ("", "", "", "", "")
    t1 = ("Desactivado", "0", "0", "0")
    first_q = brand_info["questions"][0]
    t2 = ("Awareness marcas", first_q, "0", "0")
else:
    d_ent, d_ali, d_nor = ["Marca 1", "Marca 2"], {"Marca 1": ["marca 1", "m1"], "Marca 2": ["marca 2", "m2"]}, []
    d_demo = ("", "", "", "", "")
    t1 = ("Análisis 1", "0", "0", "0")
    t2 = ("Análisis 2", "0", "0", "0")

K = mode.split(" ")[0]  # sufijo de claves

# 1. Columnas del archivo
with st.container(border=True):
    st.markdown("### 📋 Columnas del archivo (para copiar prefijos)")
    st.dataframe(pd.DataFrame({"Columna": df.columns}), hide_index=True, height=180, use_container_width=True)

# 2. Entidades, alias y normalizaciones
with st.container(border=True):
    st.markdown("### 🏷️ 1. Entidades, alias y normalizaciones")
    col_a, col_b = st.columns(2)
    with col_a:
        entities_text = st.text_area("Entidades a evaluar, una por línea", "\n".join(d_ent), height=180, key=f"ent::{K}")
    with col_b:
        aliases_text = st.text_area("Alias / condiciones en JSON", json.dumps(d_ali, ensure_ascii=False, indent=2),
                                    height=180, key=f"ali::{K}")
    
    norm_text = st.text_area("Normalizaciones opcionales en JSON", json.dumps(d_nor, ensure_ascii=False, indent=2),
                             height=120, key=f"nor::{K}")

try:
    aliases, normalizations = json.loads(aliases_text), json.loads(norm_text)
except Exception as exc:  # noqa: BLE001
    st.error(f"⚠️ Error en las estructuras JSON: {exc}")
    st.stop()

entities = [line.strip() for line in entities_text.splitlines() if line.strip()]

# 3. Preguntas y demográficos
with st.container(border=True):
    st.markdown("### ⚙️ 2. Preguntas y demográficos")
    st.caption("Escribe el prefijo (o parte del nombre) de la columna. Usa 0 para desactivar.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Demográficos**")
        sexo = st.text_input("Sexo", d_demo[0], key=f"sx::{K}")
        edad = st.text_input("Edad", d_demo[1], key=f"ed::{K}")
        depto = st.text_input("Departamento / Ciudad", d_demo[2], key=f"dp::{K}")
        estrato = st.text_input("Estrato", d_demo[3], key=f"es::{K}")
        ingreso = st.text_input("Ingreso / Rangos", d_demo[4], key=f"in::{K}")
    with col2:
        st.markdown("**Análisis 1**")
        a1_name = st.text_input("Nombre análisis 1", t1[0], key=f"n1::{K}")
        a1_tom = st.text_input("TOM análisis 1", t1[1], key=f"t1::{K}")
        a1_esp = st.text_area("Espontáneo análisis 1", t1[2], height=100, key=f"e1::{K}")
        a1_ayu = st.text_area("Ayudado análisis 1", t1[3], height=100, key=f"y1::{K}")
    with col3:
        st.markdown("**Análisis 2**")
        a2_name = st.text_input("Nombre análisis 2", t2[0], key=f"n2::{K}")
        a2_tom = st.text_input("TOM análisis 2", t2[1], key=f"t2::{K}")
        a2_esp = st.text_area("Espontáneo análisis 2", t2[2], height=100, key=f"e2::{K}")
        a2_ayu = st.text_area("Ayudado análisis 2", t2[3], height=100, key=f"y2::{K}")

demo_cols = {"sexo": aw.find_col(df, sexo), "edad": aw.find_col(df, edad), "departamento": aw.find_col(df, depto),
             "estrato": aw.find_col(df, estrato), "ingreso": aw.find_col(df, ingreso)}
cfg1 = {"name": a1_name, "tom": a1_tom, "esp": a1_esp, "ayu": a1_ayu}
cfg2 = {"name": a2_name, "tom": a2_tom, "esp": a2_esp, "ayu": a2_ayu}
active = [c for c in (cfg1, cfg2) if any(c[k].strip() not in ("0", "") for k in ("tom", "esp", "ayu"))]

# 4. Validación de columnas
st.write("---")
st.subheader("3. Validación de columnas")
rows = [{"Tipo": "Demográfico", "Campo": k, "Columna detectada": str(v)} for k, v in demo_cols.items()]
for label, cfg in (("Análisis 1", cfg1), ("Análisis 2", cfg2)):
    if cfg in active:
        rows += [{"Tipo": label, "Campo": "TOM", "Columna detectada": str(aw.find_col(df, cfg["tom"]))},
                 {"Tipo": label, "Campo": "Espontáneo", "Columna detectada": ", ".join(aw.find_cols(df, cfg["esp"]))},
                 {"Tipo": label, "Campo": "Ayudado", "Columna detectada": ", ".join(aw.find_cols(df, cfg["ayu"]))}]
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# 5. Resultados
st.subheader("4. Resultados")
if not active:
    st.info("Configura al menos un análisis (TOM, Espontáneo o Ayudado) en la sección 2.")
    st.stop()
if not entities:
    st.warning("Agrega al menos una entidad.")
    st.stop()

if st.button("📊 Calcular awareness", type="primary"):
    try:
        results = {}
        for cfg in active:
            _, indicators, _ = aw.build_analysis(df, demo_cols, cfg, entities, aliases, normalizations, 0)
            label = cfg["name"] if cfg["name"] not in results else f"{cfg['name']} (2)"
            results[label] = {"indicators": indicators, "cfg": cfg}
        st.session_state["awareness"] = {"results": results, "entities": entities}
        st.session_state["awareness_xlsx"] = aw.build_excel_bytes(
            df, demo_cols, cfg1, cfg2, entities, aliases, normalizations, 0)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Error: {exc}")

saved = st.session_state.get("awareness")
if saved:
    tabs = st.tabs(list(saved["results"].keys()))
    for tab, (name, res) in zip(tabs, saved["results"].items()):
        with tab:
            ind, ents = res["indicators"], saved["entities"]
            seg_options = ["Total"] + [f"{k}: {v}" for k, v in demo_cols.items() if v]
            seg = st.selectbox("Ver por", seg_options, key=f"seg::{name}")
            if seg == "Total":
                table = aw.category_table(ind, df, None, None, ents)
            else:
                col = demo_cols[seg.split(":")[0]]
                value = st.selectbox("Valor", list(pd.Series(df[col].fillna("Sin dato")).drop_duplicates()), key=f"val::{name}")
                table = aw.category_table(ind, df, col, value, ents)
            order = table.sort_values("AWA %", ascending=False)["Entidad"].tolist()
            long = table.melt(id_vars="Entidad", value_vars=["TOM %", "Espontaneo %", "Ayudado %"],
                              var_name="Nivel", value_name="Valor")
            long["Nivel"] = long["Nivel"].str.replace(" %", "", regex=False)
            fig = px.bar(long, x="Valor", y="Entidad", color="Nivel", orientation="h", barmode="stack",
                         category_orders={"Entidad": order, "Nivel": ["TOM", "Espontaneo", "Ayudado"]},
                         title=f"Awareness total por marca · {name}")
            fig.update_xaxes(tickformat=".0%", title="% de la base")
            fig.update_yaxes(autorange="reversed", title="")
            st.plotly_chart(ui.style_fig(fig, height=max(360, 42 * len(ents) + 140)))
            shown = table.copy()
            for c in [c for c in shown.columns if c.endswith("%")]:
                shown[c] = shown[c].map(lambda v: f"{v:.0%}")
            st.dataframe(shown, hide_index=True, use_container_width=True)

    if st.session_state.get("awareness_xlsx"):
        st.download_button(
            "📥 Descargar reporte de Awareness (Excel)", data=st.session_state["awareness_xlsx"],
            file_name="Reporte_Awareness.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )