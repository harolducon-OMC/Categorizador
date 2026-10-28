# -*- coding: utf-8 -*-
"""Utilidades para consultar el catálogo OpenAI-compatible de Hugging Face."""
from typing import Dict, List

import requests

MODELS_URL = "https://router.huggingface.co/v1/models"


def list_chat_models(token: str, timeout: int = 25) -> List[Dict]:
    """Devuelve IDs de modelos de chat activos y metadatos básicos de gratuidad."""
    if not token or not token.strip():
        raise ValueError("Ingresa un token de Hugging Face antes de consultar modelos.")

    try:
        response = requests.get(
            MODELS_URL,
            headers={"Authorization": f"Bearer {token.strip()}", "Accept": "application/json"},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise RuntimeError("No se pudo conectar con el catálogo de Hugging Face. Revisa la conexión.") from exc

    if response.status_code in (401, 403):
        raise RuntimeError(
            "Hugging Face rechazó el token. Verifica que tenga permiso «Make calls to Inference Providers»."
        )
    if response.status_code == 429:
        raise RuntimeError("Hugging Face limitó la consulta del catálogo. Espera un momento y vuelve a intentar.")
    if response.status_code >= 400:
        detail = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                detail = str(body.get("error") or body.get("message") or "")
        except ValueError:
            pass
        raise RuntimeError(f"El catálogo de Hugging Face devolvió HTTP {response.status_code}. {detail[:250]}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Hugging Face devolvió una respuesta de catálogo no válida.") from exc

    rows = payload.get("data", []) if isinstance(payload, dict) else []
    models: List[Dict] = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        model_id = str(row.get("id", "")).strip()
        if not model_id or model_id in seen:
            continue

        providers = row.get("providers") or []
        live_providers = [
            item for item in providers
            if isinstance(item, dict) and item.get("status", "live") == "live"
        ]
        if providers and not live_providers:
            continue
        models.append({
            "id": model_id,
            "is_free": any(item.get("is_free") is True for item in live_providers),
            "provider_count": len(live_providers),
        })
        seen.add(model_id)

    models.sort(key=lambda item: (not item["is_free"], item["id"].casefold()))
    if not models:
        raise RuntimeError(
            "No se encontraron modelos de chat disponibles. Revisa el token o consulta el catálogo de Inference Providers."
        )
    return models
