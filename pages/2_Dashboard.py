# -*- coding: utf-8 -*-
"""Dashboard: frecuencias, cruces por segmento, insights y reporte en Excel."""

import plotly.express as px
import streamlit as st

from core import coding, export, insights, state, ui
from core.export import short_name

ui.setup_page("Dashboard", "📈")
ui.require_login()
ui.sidebar()
ui.header("Dashboard de resultados", "Frecuencias, cruces por segmento e insights por categoría.")

df = state.require_data()
coded = st.session_state.coded
if not coded:
    st.info("Aún no hay preguntas categorizadas.")
    st.page_link("pages/1_Categorizacion.py", label="Ir a Categorización", icon="🗂️")
    st.stop()
llm = state.get_llm()

questions = list(coded.keys())
q = st.selectbox("Pregunta", questions, format_func=lambda x: short_name(x, 90))
info = coded[q]
labels, cats = info["labels"], info["categories"]
texts = df[q].fillna("").astype(str).tolist()
base = coding.valid_base(labels)

if st.button("📦 Preparar reporte Excel (datos, frecuencias, insights y validación)"):
    with st.spinner("Armando el reporte..."):
        st.session_state["report_bytes"] = export.build_report_excel(
            df, coded, st.session_state.insights, st.session_state.validation
        )
if st.session_state.get("report_bytes"):
    st.download_button(
        "📥 Descargar reporte (Excel)",
        data=st.session_state["report_bytes"],
        file_name="Reporte_Categorizacion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

tab_freq, tab_cross, tab_ins = st.tabs(["Frecuencias", "Cruces por segmento", "Insights"])

# ---------------------------------------------------------------- frecuencias
with tab_freq:
    table = coding.frequency_table(labels, cats)
    table = table[table["Menciones"] > 0]
    c1, c2 = st.columns([1, 3])
    top_n = c1.slider("Categorías a mostrar", 3, len(table), min(12, len(table))) if len(table) > 3 else len(table)
    st.caption(f"Base: {base:,} personas con respuesta válida. Una persona puede mencionar varias categorías.")
    plot = table.head(top_n)
    fig = px.bar(plot, x="%", y="Categoría", orientation="h", text="%", title=short_name(q, 90))
    fig.update_traces(texttemplate="%{x:.0%}", textposition="outside", cliponaxis=False)
    fig.update_xaxes(tickformat=".0%", title="% de personas")
    fig.update_yaxes(categoryorder="total ascending", title="")
    st.plotly_chart(ui.style_fig(fig, height=max(360, 38 * len(plot) + 120)))

# ---------------------------------------------------------------------- cruces
with tab_cross:
    candidates = [c for c in df.columns
                  if c not in coded and 2 <= df[c].nunique(dropna=True) <= 15]
    if not candidates:
        st.info("No se encontraron columnas segmentadoras (entre 2 y 15 valores distintos).")
    else:
        seg_col = st.selectbox("Segmentar por", candidates)
        used = [c for c in cats if any(c in l for l in labels)]
        matrix, bases = coding.crosstab_by_segment(labels, df[seg_col], used)
        matrix = matrix.rename(columns={k: f"{k} (n={bases[k]})" for k in matrix.columns})
        fig = px.imshow(matrix, text_auto=".0%", aspect="auto", color_continuous_scale="Blues",
                        title=f"% que menciona cada categoría según {seg_col}")
        fig.update_xaxes(side="top")
        st.plotly_chart(ui.style_fig(fig, height=max(380, 40 * len(used) + 160)))
        small = [k for k, v in bases.items() if v < 30]
        if small:
            st.warning("Segmentos con base menor a 30 (interpretar con cautela): " + ", ".join(map(str, small)))

# ------------------------------------------------------------------- insights
with tab_ins:
    st.caption("La IA redacta la explicación a partir de las respuestas reales; los porcentajes y las citas se calculan en código.")
    if st.button("🧠 Generar insights", type="primary", disabled=llm is None):
        with st.spinner("Sintetizando respuestas por categoría..."):
            try:
                st.session_state.insights[q] = insights.build_insights(llm, q, texts, labels, cats)
                st.session_state.pop("categorization_export_bytes", None)
                st.session_state.pop("report_bytes", None)
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudieron generar los insights: {exc}")
    result = st.session_state.insights.get(q)
    if result:
        if result["resumen"]:
            st.info(result["resumen"])
        for item in result["categorias"]:
            with st.container(border=True):
                st.markdown(f"**{item['categoria']}** · {item['pct']:.0%} ({item['n']} de {item['base']})")
                st.write(item["explicacion"])
                for quote in item["citas"]:
                    st.caption(f"“{quote}”")
