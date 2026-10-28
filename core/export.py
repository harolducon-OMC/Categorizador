# -*- coding: utf-8 -*-
"""
core/export.py
Reporte en Excel: datos codificados, frecuencias e insights (reutiliza el estilo de awareness).
"""

import io
import re
from typing import Dict, Optional

import pandas as pd
from openpyxl import Workbook

from core.awareness import write_main_sheet, write_sections_sheet
from core.coding import NSNR_LABEL, frequency_table, onehot, valid_base

_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def short_name(text: str, size: int = 40) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text if len(text) <= size else text[: size - 1] + "…"


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if not pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].map(lambda v: _ILLEGAL.sub("", v) if isinstance(v, str) else v)
    return out


def build_report_excel(df: pd.DataFrame, coded: Dict[str, Dict], insights: Dict[str, Dict],
                       validation: Optional[Dict[str, Dict]] = None) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)

    # 1) Datos originales + columnas codificadas
    out = df.copy().reset_index(drop=True)
    for n, (q, info) in enumerate(coded.items(), start=1):
        tag = f"P{n}"
        labels = info["labels"]
        out[f"{tag} | Categorías"] = [" | ".join(l) for l in labels]
        oh = onehot(labels, info["categories"])
        oh.columns = [f"{tag} · {short_name(c, 25)}" for c in oh.columns]
        out = pd.concat([out, oh], axis=1)
    write_main_sheet(wb, "Datos codificados", _clean(out))

    # 2) Frecuencias
    sections = []
    for n, (q, info) in enumerate(coded.items(), start=1):
        table = frequency_table(info["labels"], info["categories"])
        base = valid_base(info["labels"])
        sections.append((f"P{n} · {short_name(q, 80)}  (base: {base} con respuesta válida)", _clean(table)))
    if sections:
        write_sections_sheet(wb, "Frecuencias", sections)

    # 3) Insights
    ins_sections = []
    for n, (q, info) in enumerate(coded.items(), start=1):
        ins = insights.get(q)
        if not ins:
            continue
        rows = [{
            "Categoría": c["categoria"], "Personas": c["n"], "%": c["pct"],
            "Insight": c["explicacion"], "Cita 1": (c["citas"] + ["", ""])[0], "Cita 2": (c["citas"] + ["", ""])[1],
        } for c in ins["categorias"]]
        ins_sections.append((f"P{n} · {short_name(q, 80)}", pd.DataFrame(
            [{"Categoría": "Resumen", "Personas": "", "%": "", "Insight": ins["resumen"], "Cita 1": "", "Cita 2": ""}] + rows)))
    if ins_sections:
        write_sections_sheet(wb, "Insights", [(t, _clean(d)) for t, d in ins_sections])
        ws = wb["Insights"]
        for letter, width in (("A", 28), ("B", 10), ("C", 8), ("D", 70), ("E", 45), ("F", 45)):
            ws.column_dimensions[letter].width = width

    # 4) Validación de segunda opinión (si se ejecutó)
    val_sections = []
    for n, q in enumerate(coded, start=1):
        result = (validation or {}).get(q, {}).get("second")
        if result and not result["metrics"].empty:
            val_sections.append((f"P{n} · {short_name(q, 80)} · Métricas por categoría", _clean(result["metrics"])))
            if not result["review"].empty:
                val_sections.append((f"P{n} · Casos para revisión humana", _clean(result["review"].head(1000))))
    if val_sections:
        write_sections_sheet(wb, "Validación", val_sections)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
