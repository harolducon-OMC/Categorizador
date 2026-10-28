# -*- coding: utf-8 -*-
"""
core/validation.py
Validación de la clasificación: segunda opinión independiente + comparación con codificación manual.

IMPORTANTE (interpretación): la segunda opinión se entrena con las propias etiquetas de la IA mediante
validación cruzada. Detecta INCONSISTENCIAS (respuestas parecidas con etiquetas distintas), pero no mide
exactitud real. La exactitud real se mide con la muestra codificada a mano (compare_with_manual).
"""

import io
import re
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from core.awareness import norm
from core.coding import NSNR_LABEL, UNCLASSIFIED, group_unique

MIN_POSITIVES = 10
_ST_MODEL = None
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


def embeddings_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except Exception:  # instalación opcional ausente o parcialmente incompatible
        return False


def kappa_label(k: float) -> str:
    if k is None or (isinstance(k, float) and np.isnan(k)):
        return "n/d"
    if k >= 0.8:
        return "Muy bueno"
    if k >= 0.6:
        return "Bueno"
    if k >= 0.4:
        return "Moderado"
    return "Bajo: revisar categoría"


def _features(texts: List[str], backend: str):
    if backend == "embeddings":
        global _ST_MODEL
        from sentence_transformers import SentenceTransformer
        if _ST_MODEL is None:
            _ST_MODEL = SentenceTransformer(EMBEDDING_MODEL)
        return np.asarray(_ST_MODEL.encode(texts, normalize_embeddings=True, show_progress_bar=False))
    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True,
                          strip_accents="unicode", lowercase=True)
    return vec.fit_transform(texts)


def _kappa(a: np.ndarray, b: np.ndarray) -> float:
    from sklearn.metrics import cohen_kappa_score
    if len(a) == 0 or len(set(a)) < 2 and len(set(b)) < 2:
        return float("nan")
    try:
        return float(cohen_kappa_score(a, b))
    except ValueError:
        return float("nan")


def second_opinion(texts: Sequence[str], labels: List[List[str]], categories: Sequence[str],
                   backend: str = "tfidf", folds: int = 5, lo: float = 0.2, hi: float = 0.8) -> Dict:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    groups, rep = group_unique(texts)
    keys = list(groups)
    n_u = len(keys)
    result = {"metrics": pd.DataFrame(), "review": pd.DataFrame(), "skipped": [], "agreement": None, "flagged": 0}
    if n_u < 2 * MIN_POSITIVES:
        result["skipped"] = list(categories)
        return result

    row_u = np.full(len(texts), -1)
    for u, k in enumerate(keys):
        for r in groups[k]:
            row_u[r] = u
    valid_rows = np.where(row_u >= 0)[0]
    u_labels = [labels[groups[k][0]] for k in keys]
    X = _features([rep[k] for k in keys], backend)

    cats = [c for c in categories if c not in (NSNR_LABEL, UNCLASSIFIED)]
    proba: Dict[str, np.ndarray] = {}
    metrics, skipped = [], []
    flags: Dict[int, List[str]] = {}
    for c in cats:
        y_u = np.array([int(c in l) for l in u_labels])
        pos = int(y_u.sum())
        if pos < MIN_POSITIVES or (n_u - pos) < MIN_POSITIVES:
            skipped.append(c)
            continue
        k_folds = max(2, min(folds, pos, n_u - pos))
        cv = StratifiedKFold(n_splits=k_folds, shuffle=True, random_state=0)
        clf = LogisticRegression(max_iter=1000, class_weight="balanced", C=2.0)
        p_u = cross_val_predict(clf, X, y_u, cv=cv, method="predict_proba")[:, 1]
        proba[c] = p_u
        y_r = y_u[row_u[valid_rows]]
        p_r = p_u[row_u[valid_rows]]
        pred_r = (p_r >= 0.5).astype(int)
        bad_ai = (y_r == 1) & (p_r < lo)
        bad_2o = (y_r == 0) & (p_r > hi)
        for r, a, b in zip(valid_rows, bad_ai, bad_2o):
            if a or b:
                flags.setdefault(int(r), []).append(c)
        kappa = _kappa(y_r, pred_r)
        metrics.append({"Categoría": c, "Respuestas (IA)": int(y_r.sum()), "Kappa": round(kappa, 2) if not np.isnan(kappa) else np.nan,
                        "Acuerdo %": float((y_r == pred_r).mean()), "Lectura": kappa_label(kappa),
                        "A revisar": int(bad_ai.sum() + bad_2o.sum())})

    review_rows = []
    for r, bad_cats in sorted(flags.items()):
        u = row_u[r]
        suggested = [c for c, p in proba.items() if p[u] >= 0.5]
        review_rows.append({"Fila": r, "Respuesta": str(texts[r]), "Clasificación IA": " | ".join(labels[r]),
                            "Segunda opinión sugiere": " | ".join(suggested) or "(ninguna)",
                            "Categorías en desacuerdo": " | ".join(bad_cats)})
    result.update(
        metrics=pd.DataFrame(metrics), review=pd.DataFrame(review_rows), skipped=skipped,
        agreement=(1 - len(flags) / len(valid_rows)) if len(valid_rows) else None, flagged=len(flags),
    )
    return result


# --------------------------------------------------------- codificación manual
def sample_for_manual(texts: Sequence[str], categories: Sequence[str], n: int = 100, seed: int = 42) -> bytes:
    """Excel para codificar a ciegas (sin mostrar la clasificación de la IA)."""
    groups, rep = group_unique(texts)
    firsts = [rows[0] for rows in groups.values()]
    rng = np.random.default_rng(seed)
    chosen = sorted(rng.choice(firsts, size=min(n, len(firsts)), replace=False).tolist()) if firsts else []
    sheet = pd.DataFrame({"Fila": chosen, "Respuesta": [str(texts[i]) for i in chosen], "Codigo manual": ""})
    guide = pd.DataFrame({"Categorías válidas (separa varias con |)": list(categories)})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        sheet.to_excel(xw, sheet_name="Codificar", index=False)
        guide.to_excel(xw, sheet_name="Categorias", index=False)
        xw.sheets["Codificar"].column_dimensions["B"].width = 80
        xw.sheets["Codificar"].column_dimensions["C"].width = 40
        xw.sheets["Categorias"].column_dimensions["A"].width = 50
    return buf.getvalue()


def parse_manual(sheet: pd.DataFrame, categories: Sequence[str]) -> Tuple[Dict[int, List[str]], List[str]]:
    """Lee 'Fila' y 'Codigo manual'. Devuelve ({fila: categorías}, textos no reconocidos)."""
    lookup = {norm(c): c for c in categories}
    manual, unknown = {}, []
    for _, row in sheet.iterrows():
        code = row.get("Codigo manual")
        if pd.isna(code) or not str(code).strip():
            continue
        found = []
        for piece in re.split(r"[|;]", str(code)):
            piece = piece.strip()
            if not piece:
                continue
            match = lookup.get(norm(piece))
            if match:
                found.append(match)
            else:
                unknown.append(piece)
        if found:
            manual[int(row["Fila"])] = found
    return manual, sorted(set(unknown))


def compare_with_manual(labels: List[List[str]], manual: Dict[int, List[str]],
                        categories: Sequence[str]) -> Tuple[pd.DataFrame, Dict]:
    rows = sorted(manual)
    cats = [c for c in categories if c not in (NSNR_LABEL, UNCLASSIFIED)]
    table = []
    for c in cats:
        y_ai = np.array([int(c in labels[r]) for r in rows])
        y_m = np.array([int(c in manual[r]) for r in rows])
        if y_ai.sum() + y_m.sum() == 0:
            continue
        k = _kappa(y_m, y_ai)
        table.append({"Categoría": c, "Manual": int(y_m.sum()), "IA": int(y_ai.sum()),
                      "Kappa": round(k, 2) if not np.isnan(k) else np.nan,
                      "Acuerdo %": float((y_ai == y_m).mean()), "Lectura": kappa_label(k)})
    exact = float(np.mean([set(labels[r]) == set(manual[r]) for r in rows])) if rows else 0.0
    return pd.DataFrame(table), {"n": len(rows), "exact": exact}
