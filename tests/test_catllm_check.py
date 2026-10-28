# -*- coding: utf-8 -*-
"""Pruebas offline: no importan cat-stack ni realizan llamadas a proveedores."""
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import catllm_check, coding


class CatSurveyCheckTests(unittest.TestCase):
    def test_provider_mapping_is_explicit(self):
        self.assertEqual(catllm_check.catstack_provider("gemini"), "google")
        self.assertEqual(catllm_check.catstack_provider("google"), "google")
        self.assertEqual(catllm_check.catstack_provider("anthropic"), "anthropic")
        self.assertIsNone(catllm_check.catstack_provider("openrouter"))
        self.assertIsNone(catllm_check.catstack_provider("groq"))

    def test_run_deduplicates_and_restores_original_rows(self):
        captured = {}

        def fake_classify(**kwargs):
            captured.update(kwargs)
            n = len(kwargs["input_data"])
            return pd.DataFrame({
                "processing_status": ["success"] * n,
                "category_1": [1] * n,
                "category_2": [0] * n,
            })

        fake_module = SimpleNamespace(classify=fake_classify)
        with patch.object(catllm_check, "_import", return_value=fake_module):
            labels, stats = catllm_check.run_catsurvey(
                question="¿Qué piensa?",
                texts=["Buena calidad", "no sé", "BUENA CALIDAD", ""],
                category_names=["Calidad"],
                provider="gemini",
                model="gemini-test",
                api_key="fake-key",
            )

        self.assertEqual(captured["model_source"], "google")
        self.assertEqual(captured["user_model"], "gemini-test")
        self.assertEqual(captured["batch_mode"], False)
        self.assertEqual(len(captured["input_data"]), 1)
        self.assertEqual(labels, [["Calidad"], [coding.NSNR_LABEL], ["Calidad"], [coding.NSNR_LABEL]])
        self.assertEqual(stats["unique_texts"], 1)
        self.assertEqual(stats["failed_unique_texts"], 0)

    def test_technical_failure_is_not_other(self):
        labels, failed = catllm_check._to_labels(
            pd.DataFrame({
                "processing_status": ["error"],
                "category_1": [0],
                "category_2": [0],
            }),
            ["Calidad", coding.OTHER],
            1,
        )
        self.assertEqual(labels, [[coding.UNCLASSIFIED]])
        self.assertEqual(failed, 1)

    def test_missing_category_column_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Faltan"):
            catllm_check._to_labels(pd.DataFrame({"category_1": [1]}), ["Calidad", coding.OTHER], 1)

    def test_large_main_classifier_processes_all_unique_rows(self):
        class FakeLLM:
            fast = "fake-fast"
            smart = "fake-smart"

            def __init__(self):
                self.calls = 0

            def json(self, system, user, model=None, max_tokens=2000):
                self.calls += 1
                if "Asigna cada respuesta" not in system:
                    raise AssertionError("Unexpected prompt")
                import json
                payload = json.loads(user.split("Respuestas a clasificar:\n", 1)[1])
                return {"resultados": [
                    {"id": item["id"], "categorias": ["Calidad"]}
                    for item in payload
                ]}

        fake = FakeLLM()
        unique_texts = [f"respuesta abierta número {i}" for i in range(1200)]
        texts = unique_texts + [unique_texts[0], "no sé", ""]
        labels, stats = coding.classify(
            fake, "¿Qué opina?", texts,
            [{"nombre": "Calidad", "descripcion": "Opinión general"}],
            batch_size=30, workers=4,
        )
        self.assertEqual(len(labels), 1203)
        self.assertEqual(stats["unique_texts"], 1200)
        self.assertEqual(stats["unclassified"], 0)
        self.assertEqual(fake.calls, 40)
        self.assertEqual(labels[0], ["Calidad"])
        self.assertEqual(labels[1200], ["Calidad"])
        self.assertEqual(labels[1201], [coding.NSNR_LABEL])
        self.assertEqual(labels[1202], [coding.NSNR_LABEL])


if __name__ == "__main__":
    unittest.main(verbosity=2)
