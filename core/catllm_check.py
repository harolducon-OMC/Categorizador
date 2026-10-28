# -*- coding: utf-8 -*-
"""Integración opcional de cat-survey/cat-llm como segunda opinión.

El clasificador principal sigue siendo core.coding.classify. Esta integración
sirve para comparar una muestra controlada, no para sustituir automáticamente
la codificación guardada. cat-survey/cat-stack están publicados bajo GPL-3.0-or-later.
"""

import importlib
import inspect
import re
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

from core.coding import NSNR_LABEL, OTHER, UNCLASSIFIED, group_unique, is_nsnr
from core.awareness import norm

# Mapeo explícito: no se asume que gateways OpenAI-compatible sean equivalentes
# a un backend directo de cat-stack.
APP_TO_CATSTACK_PROVIDER = {
    "gemini": "google",
    "google": "google",
    "anthropic": "anthropic",
}


def _import():
    """Importa el paquete solo si la instalación opcional está disponible."""
    for name in ("catsurvey", "cat_survey"):
        try:
            return importlib.import_module(name)
        except ImportError:
            continue
    return None


def catsurvey_available() -> bool:
    return _import() is not None


def catstack_provider(app_provider: str) -> Optional[str]:
    """Traduce únicamente proveedores configurados y comprobables en esta app."""
    return APP_TO_CATSTACK_PROVIDER.get(str(app_provider or "").strip().lower())


def supports_provider(app_provider: str) -> bool:
    return catstack_provider(app_provider) is not None


def _filter_kwargs(func, kwargs: Dict) -> Dict:
    """Permite compatibilidad con firmas estrictas o con **kwargs de cat-survey."""
    try:
        params = inspect.signature(func).parameters
    except (TypeError, ValueError):
        return kwargs
    if any(p.kind == p.VAR_KEYWORD for p in params.values()):
        return kwargs
    return {key: value for key, value in kwargs.items() if key in params}


def _truthy(value) -> bool:
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "1.0", "true", "yes", "si", "sí"}


def _to_labels(df: pd.DataFrame, categories: Sequence[str], n_rows: int) -> Tuple[List[List[str]], int]:
    """Valida forma, categorías y estados; fallos técnicos no se confunden con Otros."""
    if len(df) != n_rows:
        raise RuntimeError(f"cat-survey devolvió {len(df)} filas y se enviaron {n_rows}.")

    by_pos = {}
    for col in df.columns:
        match = re.fullmatch(r"category_(\d+)", str(col))
        if match:
            by_pos[int(match.group(1))] = col

    if by_pos:
        mapping = {categories[i - 1]: col for i, col in by_pos.items() if 1 <= i <= len(categories)}
    else:
        by_name = {norm(col): col for col in df.columns}
        mapping = {category: by_name[norm(category)] for category in categories if norm(category) in by_name}

    missing = [category for category in categories if category not in mapping]
    if missing:
        raise RuntimeError(
            "cat-survey no devolvió todas las columnas de categoría. "
            f"Faltan: {missing[:10]}; recibidas: {[str(c) for c in df.columns][:20]}"
        )

    status_col = df["processing_status"] if "processing_status" in df.columns else None
    labels: List[List[str]] = []
    failed = 0
    for row_index in range(n_rows):
        if status_col is not None:
            status = status_col.iloc[row_index]
            status = "success" if pd.isna(status) or not str(status).strip() else str(status).strip().lower()
            if status != "success":
                labels.append([UNCLASSIFIED])
                failed += 1
                continue
        assigned = [category for category in categories if _truthy(df.iloc[row_index][mapping[category]])]
        labels.append(assigned or [OTHER])
    return labels, failed


def run_catsurvey(
    question: str,
    texts: Sequence,
    category_names: Sequence[str],
    provider: str,
    model: str,
    api_key: str,
    context: str = "",
    multi_label: bool = True,
    progress_callback=None,
) -> Tuple[List[List[str]], Dict]:
    """Clasifica los textos entregados con cat-survey y devuelve (etiquetas, métricas).

    El caller debe decidir el tamaño de la muestra. En la interfaz se limita a una
    muestra explícita para que la comparación no lance cientos o miles de llamadas
    sin que la persona conozca el alcance y costo potencial.
    """
    mod = _import()
    if mod is None:
        raise RuntimeError("cat-survey no está instalado. Ejecuta: pip install -r requirements-validation.txt")
    provider_id = catstack_provider(provider)
    if provider_id is None:
        raise ValueError(
            "cat-survey está conectado en esta versión a Gemini (Google) y Anthropic directos. "
            "Groq, Cohere y OpenRouter no se enrutan como si fueran esos proveedores."
        )
    if not api_key:
        raise ValueError("No se encontró una API key activa para el proveedor seleccionado.")
    if not model:
        raise ValueError("Selecciona un ID de modelo válido antes de ejecutar cat-survey.")

    groups, representatives = group_unique(texts)
    keys = list(groups)
    if not keys:
        return [[NSNR_LABEL] for _ in texts], {
            "unique_texts": 0, "failed_unique_texts": 0, "provider": provider_id, "model": model,
        }

    categories = list(dict.fromkeys(str(name).strip() for name in category_names if str(name).strip()))
    if not categories:
        raise ValueError("Debes definir al menos una categoría antes de comparar.")
    normalized = [norm(category) for category in categories]
    if len(normalized) != len(set(normalized)):
        raise ValueError("El catálogo contiene nombres de categorías duplicados o equivalentes.")
    if OTHER not in categories:
        categories.append(OTHER)

    description = f"Pregunta abierta: {question.strip()}"
    if context.strip():
        description += f"\nContexto del estudio: {context.strip()}"

    # No se activa batch_mode: el modo remoto es asíncrono y no ofrece progreso
    # compatible con una petición interactiva de Streamlit.
    kwargs = {
        "input_data": [representatives[key] for key in keys],
        "categories": categories,
        "description": description,
        "api_key": api_key,
        "user_model": model,
        "model_source": provider_id,
        "prompt_style": "current",
        "multi_label": bool(multi_label),
        "add_other": False,
        "check_verbosity": False,
        "batch_mode": False,
        "fail_strategy": "partial",
        "max_retries": 2,
        "json_retries": 1,
        "retry_delay": 1.0,
        "progress_callback": progress_callback,
    }
    out = mod.classify(**_filter_kwargs(mod.classify, kwargs))
    frame = out.copy() if isinstance(out, pd.DataFrame) else pd.DataFrame(out)
    frame = frame.reset_index(drop=True)
    unique_labels, failed = _to_labels(frame, categories, len(keys))

    row_labels: List[List[str]] = [[] for _ in texts]
    for row, text in enumerate(texts):
        if is_nsnr(text):
            row_labels[row] = [NSNR_LABEL]
    for unique_index, key in enumerate(keys):
        for row in groups[key]:
            row_labels[row] = list(unique_labels[unique_index])

    return row_labels, {
        "unique_texts": len(keys),
        "failed_unique_texts": failed,
        "provider": provider_id,
        "model": model,
    }
