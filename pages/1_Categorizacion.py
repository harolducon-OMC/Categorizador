# -*- coding: utf-8 -*-
"""Categorización de preguntas abiertas: temas/motivos y marcas."""

import hashlib

import pandas as pd
import streamlit as st

from core import brands, coding, export, state, topics, ui, validation
from core.export import short_name

ui.setup_page("Categorización", "🗂️")
ui.require_login()
ui.sidebar()
ui.header("Categorización de preguntas abiertas",
          "Elige las preguntas, revisa las categorías propuestas por la IA y clasifica las respuestas.")

df = state.require_data()
llm = state.get_llm()
if llm is None:
    st.warning("Configura la API key de la IA (barra lateral o Secrets) para proponer y clasificar categorías.")


def qid(question: str) -> str:
    return hashlib.md5(question.encode("utf-8")).hexdigest()[:8]


def progress_cb(bar):
    return lambda p, msg: bar.progress(min(max(p, 0.0), 1.0), text=msg)


# --------------------------------------------------------------- validación
def validation_panel(q: str, texts: list) -> None:
    key = qid(q)
    info = st.session_state.coded[q]
    stored = st.session_state.validation.setdefault(q, {})
    with st.expander("🔍 Validación de la clasificación (segunda opinión y codificación manual)"):
        st.caption(
            "La segunda opinión detecta inconsistencias entre respuestas parecidas; no mide exactitud real. "
            "Para medirla, compara con una muestra codificada a mano."
        )
        options = ["Ligero (TF-IDF)"] + (
            ["Embeddings multilingües"] if validation.embeddings_available() else []
        )
        choice = st.radio("Método de segunda opinión", options, horizontal=True, key=f"vb::{key}")
        if len(options) == 1:
            st.caption("Embeddings no instalados (opcional): ejecuta `pip in" \
            "stall -r requirements-extra.txt`.")
        if st.button("Ejecutar segunda opinión", key=f"vrun::{key}"):
            with st.spinner("Analizando consistencia con validación cruzada..."):
                try:
                    stored["second"] = validation.second_opinion(
                        texts, info["labels"], info["categories"],
                        backend="embeddings" if choice.startswith("Embeddings") else "tfidf",
                    )
                    st.session_state.pop("categorization_export_bytes", None)
                    st.session_state.pop("report_bytes", None)
                except Exception as exc:  # noqa: BLE001
                    st.error(f"No se pudo ejecutar la validación: {exc}")
        result = stored.get("second")
        if result:
            if result["metrics"].empty:
                st.warning("No hay suficientes respuestas distintas por categoría para validar (se requieren ~10 por categoría).")
            else:
                c1, c2 = st.columns(2)
                c1.metric("Respuestas sin discrepancias", f"{result['agreement']:.0%}")
                c2.metric("Casos a revisar", f"{result['flagged']:,}")
                shown = result["metrics"].copy()
                shown["Acuerdo %"] = shown["Acuerdo %"].map(lambda value: f"{value:.0%}")
                st.dataframe(shown, hide_index=True)
                if result["skipped"]:
                    st.caption("Sin casos suficientes para validar: " + ", ".join(result["skipped"]))
                if not result["review"].empty:
                    st.markdown("**Casos para revisión humana** (la IA y la segunda opinión no coinciden)")
                    st.dataframe(result["review"].head(300), hide_index=True)

        st.markdown("---")
        st.markdown("**Exactitud real: muestra codificada a mano**")
        sample_size = st.number_input("Tamaño de la muestra", 30, 300, 100, key=f"vn::{key}")
        st.download_button(
            "📥 Descargar muestra para codificar (sin mostrar la clasificación de la IA)",
            data=validation.sample_for_manual(texts, info["categories"], int(sample_size)),
            file_name="muestra_codificacion_manual.xlsx", key=f"vdl::{key}",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.caption("Completa *Codigo manual* usando las categorías de la hoja *Categorias* (varias separadas por |) y sube el archivo.")
        upload = st.file_uploader("Sube la muestra codificada", type=["xlsx"], key=f"vup::{key}")
        if upload is not None:
            try:
                sheet = pd.read_excel(upload, sheet_name="Codificar", engine="openpyxl")
                manual, unknown = validation.parse_manual(sheet, info["categories"])
                if not manual:
                    st.warning("No se encontraron códigos manuales reconocibles.")
                else:
                    table, total = validation.compare_with_manual(
                        info["labels"], manual, info["categories"]
                    )
                    st.metric(
                        "Coincidencia exacta con tu codificación", f"{total['exact']:.0%}",
                        help=f"{total['n']} respuestas comparadas",
                    )
                    shown = table.copy()
                    shown["Acuerdo %"] = shown["Acuerdo %"].map(lambda value: f"{value:.0%}")
                    st.dataframe(shown, hide_index=True)
                    if unknown:
                        st.warning("Códigos no reconocidos (se ignoraron): " + ", ".join(unknown[:10]))
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo leer el archivo de validación: {exc}")


# ---------------------------------------------------------------- resultados
def show_results(q: str, texts: list) -> None:
    info = st.session_state.coded.get(q)
    if not info:
        return
    labels, cats = info["labels"], info["categories"]
    table = coding.frequency_table(labels, cats)
    base = coding.valid_base(labels)
    n_nsnr = sum(1 for l in labels if coding.NSNR_LABEL in l)
    n_uncl = sum(1 for l in labels if coding.UNCLASSIFIED in l)

    st.markdown("#### Resultados")
    m1, m2, m3 = st.columns(3)
    m1.metric("Base (respuesta válida)", f"{base:,}")
    m2.metric("NS/NR", f"{n_nsnr:,}")
    m3.metric("Sin clasificar", f"{n_uncl:,}")
    if n_uncl:
        st.warning("Algunas respuestas no se pudieron clasificar (error de la API o límite de uso). "
                   "Vuelve a ejecutar la clasificación para completarlas.")

    shown = table.copy()
    shown["%"] = shown["%"].map(lambda v: f"{v:.0%}")
    st.dataframe(shown, hide_index=True)

    options = ["(todas)"] + [c for c in cats if c in set(table["Categoría"])]
    chosen = st.selectbox("Auditar: ver respuestas de una categoría", options, key=f"aud::{qid(q)}")
    audit = pd.DataFrame({"Respuesta": texts, "Categorías": [" | ".join(l) for l in labels]})
    if chosen != "(todas)":
        audit = audit[[chosen in l for l in labels]]
    st.dataframe(audit.head(300), hide_index=True)
    st.caption("Muestra de hasta 300 filas. La descarga al final de esta página contiene la base completa.")
    if info.get("kind") == "temas":
        validation_panel(q, texts)


# --------------------------------------------------------------------- temas
def theme_flow(q: str, texts: list) -> None:
    key = qid(q)
    c1, c2 = st.columns([3, 1])
    context = c1.text_input("Contexto del estudio (opcional)", key=f"ctx::{key}",
                            placeholder="Ej.: Percepción de zapatos deportivos de cuero")
    max_cat = c2.number_input("Máx. categorías", 3, 20, 10, key=f"max::{key}")

    method = "IA (LLM)"
    unique_n = len(coding.group_unique(texts)[0])
    if topics.bertopic_available():
        method = st.radio(
            "Método para proponer categorías",
            ["IA (LLM)", "BERTopic + IA (mínimo 60 respuestas distintas)"],
            horizontal=True,
            key=f"meth-v2::{key}", help="BERTopic agrupa respuestas por similitud semántica; la IA nombra y describe los grupos.",
        )
        st.caption(f"Respuestas distintas válidas en esta pregunta: {unique_n:,}.")
        if method.startswith("BERTopic") and unique_n < topics.MIN_UNIQUE_TEXTS:
            st.warning(
                f"BERTopic necesita al menos {topics.MIN_UNIQUE_TEXTS} respuestas distintas; "
                f"esta pregunta tiene {unique_n}. Selecciona **IA (LLM)** para continuar con esta muestra."
            )
    else:
        st.caption(
            "Usando **IA (LLM)** con el proveedor y modelo de la barra lateral. "
            "BERTopic es opcional."
        )

    use_bertopic = method.startswith("BERTopic")
    too_few_for_bertopic = use_bertopic and unique_n < topics.MIN_UNIQUE_TEXTS
    if st.button(
        "✨ Proponer categorías con el método seleccionado", key=f"disc::{key}",
        disabled=llm is None or too_few_for_bertopic,
    ):
        with st.spinner("Analizando las respuestas..."):
            try:
                if use_bertopic:
                    frame = topics.discover_with_bertopic(llm, q, texts, int(max_cat), context=context)
                else:
                    frame = coding.discover_categories(llm, q, texts, int(max_cat), context=context)
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudieron proponer categorías: {exc}")
            else:
                st.session_state.codeframes[q] = pd.DataFrame(frame, columns=["nombre", "descripcion"])
                st.session_state.pop(f"cf::{key}", None)

    base = st.session_state.codeframes.get(q, pd.DataFrame({"nombre": pd.Series(dtype="str"),
                                                           "descripcion": pd.Series(dtype="str")}))
    st.markdown("**Categorías** — edita, agrega o elimina filas (también puedes escribir las tuyas).")
    edited = st.data_editor(
        base, num_rows="dynamic", key=f"cf::{key}",
        column_config={
            "nombre": st.column_config.TextColumn("Categoría", required=True),
            "descripcion": st.column_config.TextColumn("Qué incluye", width="large"),
        },
    )
    codeframe = [
        {"nombre": str(r.nombre).strip(), "descripcion": "" if pd.isna(r.descripcion) else str(r.descripcion).strip()}
        for r in edited.itertuples() if not pd.isna(r.nombre) and str(r.nombre).strip()
    ]
    multi = st.checkbox("Permitir varias categorías por respuesta", True, key=f"multi::{key}")

    if st.button("🚀 Clasificar respuestas", type="primary", key=f"run::{key}",
                 disabled=llm is None or not codeframe):
        bar = st.progress(0.0, text="Iniciando...")
        try:
            labels, stats = coding.classify(llm, q, texts, codeframe, multi=multi, context=context,
                                            progress=progress_cb(bar))
        except Exception as exc:  # noqa: BLE001
            bar.empty()
            st.error(f"Error al clasificar: {exc}")
        else:
            bar.empty()
            names = [c["nombre"] for c in codeframe]
            st.session_state.coded[q] = {"kind": "temas", "labels": labels,
                                         "categories": coding.categories_in_use(labels, names)}
            st.session_state.pop("categorization_export_bytes", None)
            st.session_state.insights.pop(q, None)
            st.session_state.validation.pop(q, None)
            if stats["errors"]:
                st.warning(f"Hubo errores parciales: {stats['errors'][0]}")
    show_results(q, texts)


# --------------------------------------------------------------------- marcas
def brand_flow(q: str, texts: list) -> None:
    key = qid(q)
    known = st.text_area("Marcas conocidas (opcional, una por línea)", key=f"known::{key}", height=90,
                         help="Ayuda a unificar nombres: si la persona escribe 'bancolonbia', se normaliza a tu lista.")
    if st.button("🔎 Detectar marcas", type="primary", key=f"det::{key}", disabled=llm is None):
        bar = st.progress(0.0, text="Iniciando...")
        try:
            raw = brands.extract_mentions(llm, q, texts, known_brands=known.splitlines(), progress=progress_cb(bar))
        except Exception as exc:  # noqa: BLE001
            bar.empty()
            st.error(f"Error al detectar marcas: {exc}")
        else:
            bar.empty()
            st.session_state.brand_raw[q] = raw
            st.session_state.coded.pop(q, None)
            st.session_state.pop("categorization_export_bytes", None)
            st.session_state.validation.pop(q, None)

    raw = st.session_state.brand_raw.get(q)
    if raw is None:
        return
    thr = st.slider("Sensibilidad para agrupar variantes (más alto = más estricto)", 70, 100, 88, key=f"thr::{key}")
    mapping_df = brands.build_mapping(raw, thr)
    if mapping_df.empty:
        st.warning("No se detectaron marcas en esta pregunta.")
        return
    st.markdown("**Normalización de marcas** — corrige la columna *Marca normalizada* si hace falta.")
    edited = st.data_editor(
        mapping_df, hide_index=True, key=f"bm::{key}::{thr}::{len(mapping_df)}",
        disabled=["Mención", "Menciones"],
        column_config={"Marca normalizada": st.column_config.TextColumn(required=True)},
    )
    if st.button("✅ Aplicar y guardar marcas", type="primary", key=f"apply::{key}"):
        mapping = dict(zip(edited["Mención"], edited["Marca normalizada"]))
        labels = brands.apply_mapping(raw, mapping)
        entities, aliases = brands.entities_and_aliases(raw, mapping)
        st.session_state.coded[q] = {"kind": "marcas", "labels": labels, "categories": entities,
                                     "entities": entities, "aliases": aliases}
        st.session_state.pop("categorization_export_bytes", None)
        st.session_state.insights.pop(q, None)
        st.session_state.validation.pop(q, None)
        st.success("Marcas guardadas. Ya están disponibles en la página de Awareness.")
    show_results(q, texts)


# ----------------------------------------------------------------------- main
suggested = coding.suggest_open_columns(df)
questions = st.multiselect(
    "Preguntas abiertas a categorizar", options=list(df.columns), default=suggested[:10], key="open_questions",
    help="Se sugieren columnas con respuestas de texto largas y variadas. Agrega o quita las que necesites.",
)
if not questions:
    st.info("Selecciona al menos una pregunta abierta.")
    st.stop()

tabs = st.tabs([f"P{n}: {short_name(q, 26)}" for n, q in enumerate(questions, start=1)])
for tab, q in zip(tabs, questions):
    with tab:
        st.markdown(f"**{q}**")
        texts = df[q].fillna("").astype(str).tolist()
        n_valid = sum(not coding.is_nsnr(t) for t in texts)
        c1, c2, c3 = st.columns(3)
        c1.metric("Respuestas", f"{len(texts):,}")
        c2.metric("Con contenido", f"{n_valid:,}")
        c3.metric("Textos únicos", f"{len(coding.group_unique(texts)[0]):,}")
        kind = st.radio("Tipo de pregunta", ["Temas / motivos", "Marcas"], horizontal=True, key=f"kind::{qid(q)}")
        (theme_flow if kind == "Temas / motivos" else brand_flow)(q, texts)

if st.session_state.coded:
    st.divider()
    st.subheader("Descargar Excel completo categorizado")
    st.caption(
        "Incluye todas las filas y columnas originales, las categorías asignadas y columnas indicadoras, "
        "además de las frecuencias. No se limita a las 300 filas de vista previa."
    )
    if st.button("Preparar Excel completo", key="prepare_categorization_export"):
        with st.spinner("Preparando el archivo completo..."):
            try:
                st.session_state["categorization_export_bytes"] = export.build_report_excel(
                    df, st.session_state.coded, st.session_state.insights, st.session_state.validation
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo preparar el Excel: {exc}")
    if st.session_state.get("categorization_export_bytes"):
        st.download_button(
            "Descargar Excel categorizado",
            data=st.session_state["categorization_export_bytes"],
            file_name="Base_Completa_Categorizada.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_categorization_export",
        )
