# -*- coding: utf-8 -*-
"""
core/catllm_check.py
Segunda opinión con cat-survey (ecosistema cat-llm de Chris Soria): reclasifica las respuestas con un
pipeline y prompts independientes y devuelve etiquetas comparables con las de la plataforma.

Instalación:  pip install cat-survey      (licencia GPL-3.0-or-later)

cat-survey devuelve un DataFrame con una columna 0/1 por categoría (category_1, category_2, ...).
Este módulo es tolerante al formato exacto: filtra los parámetros según la firma de classify()
y reconoce las columnas por posición (category_N) o por nombre de categoría.
"""

import importlib
import inspect
import re
from typing import Dict, List, Optional, Sequence

import pandas as pd

from core.awareness import norm
from core.coding import NSNR_LABEL, OTHER, group_unique

PROVIDERS = {"Anthropic (Claude)": "anthropic", "OpenAI": "openai"}
DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-4o"}


def _import():
    for name in ("catsurvey", "cat_survey"):  # la documentación menciona ambos nombres de import
        try:
            return importlib.import_module(name)
        except ImportError:
            continue
    return None


def catsurvey_available() -> bool:
    return _import() is not None


def _filter_kwargs(func, kwargs: Dict) -> Dict:
    try:
        params = inspect.signature(func).parameters
    except (TypeError, ValueError):
        return kwargs
    if any(p.kind == p.VAR_KEYWORD for p in params.values()):
        return kwargs
    return {k: v for k, v in kwargs.items() if k in params}


def _truthy(value) -> bool:
    return str(value).strip().lower() in {"1", "1.0", "true", "yes", "si", "sí"}


def _to_labels(df: pd.DataFrame, categories: Sequence[str], n_rows: int) -> List[List[str]]:
    if len(df) != n_rows:
        raise RuntimeError(f"cat-survey devolvió {len(df)} filas y se enviaron {n_rows}.")
    by_pos = {}
    for col in df.columns:
        m = re.fullmatch(r"category_(\d+)", str(col))
        if m:
            by_pos[int(m.group(1))] = col
    if by_pos:
        mapping = {categories[i - 1]: col for i, col in by_pos.items() if 1 <= i <= len(categories)}
    else:
        by_name = {norm(c): c for c in df.columns}
        mapping = {cat: by_name[norm(cat)] for cat in categories if norm(cat) in by_name}
    if not mapping:
        raise RuntimeError("No se reconoció el formato de salida de cat-survey. "
                           f"Columnas recibidas: {[str(c) for c in df.columns][:15]}")
    flags = {cat: df[col].map(_truthy).tolist() for cat, col in mapping.items()}
    return [[cat for cat in mapping if flags[cat][i]] for i in range(n_rows)]


def run_catsurvey(question: str, texts: Sequence, category_names: Sequence[str], provider: str, model: str,
                  api_key: str, context: str = "") -> List[List[str]]:
    """Reclasifica con cat-survey. Devuelve etiquetas por fila (NS/NR -> [NSNR_LABEL])."""
    mod = _import()
    if mod is None:
        raise RuntimeError("cat-survey no está instalado. Ejecuta: pip install -r requirements-validation.txt")
    groups, rep = group_unique(texts)
    keys = list(groups)
    cats = list(category_names) + ([OTHER] if OTHER not in category_names else [])
    kwargs = dict(
        input_data=[rep[k] for k in keys], categories=cats, survey_question=question, description=context,
        api_key=api_key, user_model=model, model_source=provider, creativity=0,
        add_other=False, check_verbosity=False,  # evita preguntas interactivas por consola
    )
    out = mod.classify(**_filter_kwargs(mod.classify, kwargs))
    df = out if isinstance(out, pd.DataFrame) else pd.DataFrame(out)
    u_labels = _to_labels(df.reset_index(drop=True), cats, len(keys))

    labels: List[List[str]] = [[] for _ in texts]
    for i, t in enumerate(texts):
        if norm(t) == "" or not str(t).strip():
            labels[i] = [NSNR_LABEL]
    for u, key in enumerate(keys):
        for r in groups[key]:
            labels[r] = list(u_labels[u]) or [OTHER]
    for i, t in enumerate(texts):  # NS/NR detectados por la plataforma
        if not labels[i]:
            labels[i] = [NSNR_LABEL]
    return labels
