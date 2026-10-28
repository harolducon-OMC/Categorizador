# -*- coding: utf-8 -*-
"""Inicio: carga del archivo (Excel / CSV) y estado del proyecto."""

import pandas as pd
import streamlit as st

from core import coding, state, ui

# 1. Configuración de página e interfaz principal
ui.setup_page("Inicio", "📊")
ui.require_login()
ui.sidebar()

# Inyección de CSS avanzado para limpiar tooltips, corregir el botón de carga y estilizar métricas
st.markdown("""
<style>
    /* Oculta de forma radical cualquier tooltip o título flotante en la barra lateral */
    [data-testid="stSidebar"] [title], 
    [data-testid="stSidebarNav"] [title],
    .stSidebar [title] {
        display: none !important;
    }

    /* Oculta los iconos y spans internos defectuosos que generan texto duplicado */
    .stFileUploader section svg,
    .stFileUploader button div[data-testid="stMarkdownContainer"],
    .stFileUploader [data-testid="stFileUploadDropzone"] small {
        display: none !important;
    }

    /* Forzar limpieza absoluta del texto duplicado en el botón de carga */
    .stFileUploader button p {
        visibility: hidden;
        position: relative;
    }
    
    /* Reemplazar el texto interno del botón de carga de forma limpia */
    .stFileUploader button p::after {
        content: "📁 Examinar archivo";
        visibility: visible;
        position: absolute;
        left: 0;
        right: 0;
        top: 0;
        bottom: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white !important;
        font-weight: 600;
    }

    /* Estilo limpio para el contenedor de carga */
    .stFileUploader section {
        border: 2px dashed rgba(255, 255, 255, 0.25) !important;
        border-radius: 12px !important;
        padding: 2rem !important;
        background-color: rgba(255, 255, 255, 0.02) !important;
        text-align: center;
    }
    .stFileUploader section:hover {
        border-color: #4A90E2 !important;
        background-color: rgba(74, 144, 226, 0.05) !important;
    }

    /* Estilizado elegante para el botón de carga */
    .stFileUploader button {
        background-color: #4A90E2 !important;
        color: transparent !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.2rem !important;
    }
    .stFileUploader button:hover {
        background-color: #357ABD !important;
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

ui.header("Plataforma de Insights", "Convierte respuestas abiertas en hallazgos claros y accionables.")

# 2. Contenedor principal de carga de archivos
with st.container(border=True):
    st.subheader("📁 Carga de datos")
    st.caption("Sube un archivo en formato Excel (.xlsx) o CSV. Máximo 25 MB. Cada fila debe representar a un encuestado.")

    uploaded = st.file_uploader(
        "Cargar archivo de encuesta", 
        type=["xlsx", "csv"],
        label_visibility="collapsed",
        help="Formatos permitidos: Excel (.xlsx) y CSV. Tamaño máximo: 25 MB."
    )

    if uploaded is not None:
        if uploaded.size > 25 * 1024 * 1024:
            st.error("⚠️ El archivo supera el límite máximo permitido de 25 MB.")
            st.stop()
        
        sheet = None
        if uploaded.name.lower().endswith(".xlsx"):
            try:
                sheets = pd.ExcelFile(uploaded, engine="openpyxl").sheet_names
                if len(sheets) > 1:
                    sheet = st.selectbox("Selecciona la hoja de cálculo:", sheets)
                else:
                    sheet = sheets[0]
            except Exception:
                st.error("No se pudo leer la estructura del archivo Excel.")
                st.stop()

        sig = f"{uploaded.name}|{uploaded.size}|{sheet}"
        
        if st.session_state.get("df_sig") != sig:
            try:
                with st.spinner("Procesando y validando la base de datos..."):
                    df_new = state.read_table(uploaded, sheet)
                
                if df_new.empty:
                    st.error("⚠️ El archivo cargado no contiene registros o datos.")
                    st.stop()
                    
                if len(df_new) > 200_000 or len(df_new.columns) > 500:
                    st.error("⚠️ El archivo supera el máximo permitido (200,000 filas o 500 columnas).")
                    st.stop()
                    
                df_new.columns = [str(c).strip() for c in df_new.columns]
                state.set_data(df_new, uploaded.name, sig)
                st.success("✅ Base de datos cargada correctamente.")
            except Exception:  # noqa: BLE001
                st.error("Ocurrió un error al leer el archivo. Asegúrate de que sea un CSV o XLSX válido.")
                st.stop()

# 3. Vista previa y métricas clave
df = st.session_state.get("df")

if df is not None:
    st.write("---")
    suggested = coding.suggest_open_columns(df)
    
    st.subheader("Resumen del Dataset")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Filas", f"{len(df):,}")
    c2.metric("Total Columnas", f"{df.shape[1]:,}")
    c3.metric("Preguntas Abiertas Detectadas", f"{len(suggested)}")

    st.markdown("### Vista previa de registros")
    st.dataframe(df.head(50), use_container_width=True)
    
    st.info("💡 **Siguiente paso:** Dirígete a la sección **Categorización** desde el menú lateral para iniciar la clasificación.")

else:
    st.warning(
        "ℹ️ **Aún no has cargado un archivo.** Para probar las funcionalidades de la plataforma, "
        "puedes usar el archivo de prueba disponible en `sample_data/ejemplo_encuesta.csv`."
    )

# 4. Sección de guía rápida
st.write("---")
st.markdown("### ❓ ¿Cómo funciona el flujo de trabajo?")
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.markdown("**1 · Categoriza**\n\nElige una pregunta abierta, revisa las categorías sugeridas por la IA y clasifica las respuestas.")
with col_b:
    st.markdown("**2 · Explora resultados**\n\nConsulta tablas de frecuencia, compara datos por segmento y extrae citas clave.")
with col_c:
    st.markdown("**3 · Mide awareness**\n\nAnaliza métricas de recordación espontánea y guiada desglosadas por marca.")