from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from generate_presupuesto import generate  # noqa: E402
from render_html import render  # noqa: E402
from import_catalog_csv import import_csv_rows  # noqa: E402

SOURCE_BUDGET = Path("/home/osmarg/Nextcloud/Calculos/bess punta catalina integra/construcosto/presupuesto.json")


def assert_source_shape_compatible(testcase: unittest.TestCase, data: dict) -> None:
    for key in ["project", "currency", "taxes", "metadata", "partidas", "indirectos", "consideraciones"]:
        testcase.assertIn(key, data)
    for key in ["name", "documentTitle", "date"]:
        testcase.assertIn(key, data["project"])
    for key in ["base", "symbol", "usdRate", "showUsdConversion"]:
        testcase.assertIn(key, data["currency"])
    testcase.assertIn("itbisPercent", data["taxes"])
    testcase.assertIsInstance(data["partidas"], list)
    testcase.assertGreater(len(data["partidas"]), 0)
    for partida in data["partidas"]:
        for key in ["code", "title", "subcategories"]:
            testcase.assertIn(key, partida)
        testcase.assertIsInstance(partida["subcategories"], list)
        testcase.assertGreater(len(partida["subcategories"]), 0)
        for subcategory in partida["subcategories"]:
            for key in ["code", "title", "items"]:
                testcase.assertIn(key, subcategory)
            testcase.assertIsInstance(subcategory["items"], list)
            testcase.assertGreater(len(subcategory["items"]), 0)
            for item in subcategory["items"]:
                for key in ["code", "description", "unit", "quantity", "unitPrice"]:
                    testcase.assertIn(key, item)


class FullParityBudgetTest(unittest.TestCase):
    def test_generate_outputs_full_presupuesto_structure(self) -> None:
        request = {
            "company": "integra",
            "project": {"name": "Proyecto TDD", "client": "Integra", "location": "RD"},
            "currency": {"base": "DOP", "symbol": "RD$", "usdRate": 60, "showUsdConversion": True},
            "taxes": {"itbisPercent": 18},
            "items": [
                {"description": "concreto fc 250", "quantity": 2, "partida": "Civiles", "subcategory": "Hormigón"},
                {"description": "oficial albañil", "quantity": 3, "partida": "Civiles", "subcategory": "Mano de obra"},
            ],
            "indirectos": [{"name": "DIRECCION TECNICA", "type": "percent", "value": 10}],
            "consideraciones": {"generales": ["Nota general TDD"]},
        }
        with tempfile.TemporaryDirectory() as tmp:
            request_path = Path(tmp) / "request.json"
            output_path = Path(tmp) / "presupuesto.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")

            data = generate(request_path, output_path)

        self.assertIn("metadata", data)
        self.assertEqual(data["currency"]["base"], "DOP")
        self.assertEqual(data["taxes"]["itbisPercent"], 18)
        self.assertEqual(len(data["partidas"]), 1)
        self.assertGreaterEqual(len(data["partidas"][0]["subcategories"]), 2)
        self.assertEqual(data["indirectos"][0]["name"], "DIRECCION TECNICA")
        self.assertEqual(data["consideraciones"]["generales"], ["Nota general TDD"])

    def test_source_presupuesto_json_shape_is_supported_by_local_checker(self) -> None:
        self.assertTrue(SOURCE_BUDGET.exists())
        data = json.loads(SOURCE_BUDGET.read_text(encoding="utf-8"))

        assert_source_shape_compatible(self, data)

    def test_generated_presupuesto_json_shape_is_supported_by_local_checker(self) -> None:
        request = {
            "company": "integra",
            "project": {"name": "Proyecto Schema", "documentTitle": "Presupuesto", "date": "2026-05-28"},
            "items": [{"description": "concreto fc 250", "quantity": 1}],
            "indirectos": [{"name": "IMPREVISTOS", "type": "percent", "value": 5}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            request_path = Path(tmp) / "request.json"
            output_path = Path(tmp) / "presupuesto.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")

            data = generate(request_path, output_path)

        assert_source_shape_compatible(self, data)

    def test_render_outputs_partidas_totals_moneda_notes_glossary_markers(self) -> None:
        budget = {
            "company": "dapec",
            "project": {"name": "Proyecto Render", "client": "DAPEC", "documentTitle": "Presupuesto", "date": "2026-05-28"},
            "currency": {"base": "DOP", "symbol": "RD$", "usdRate": 60, "showUsdConversion": True},
            "taxes": {"itbisPercent": 18},
            "metadata": {"company": "dapec"},
            "partidas": [{
                "code": "1", "title": "Partida TDD", "description": "Desc", "consideraciones": ["Nota partida TDD"],
                "subcategories": [{"code": "1.1", "title": "Sub", "items": [{"code": "1.1.1", "description": "Item", "unit": "m3", "quantity": 2, "unitPrice": 100}]}],
            }],
            "indirectos": [{"name": "IMPREVISTOS", "type": "percent", "value": 5}],
            "consideraciones": {"generales": ["Nota general TDD"]},
        }
        with tempfile.TemporaryDirectory() as tmp:
            budget_path = Path(tmp) / "presupuesto.json"
            html_path = Path(tmp) / "index.html"
            budget_path.write_text(json.dumps(budget), encoding="utf-8")

            render(budget_path, output_path=html_path, static_fallback=True)
            html = html_path.read_text(encoding="utf-8")

        for marker in [
            "data-block-type=\"partida\"",
            "Subtotal de partidas",
            "Indirectos",
            "ITBIS",
            "Resumen en moneda alterna",
            "Notas y consideraciones",
            "Glosario de unidades",
            "DAPEC",
        ]:
            self.assertIn(marker, html)


class SourceRendererParityTest(unittest.TestCase):
    def test_render_prepares_source_style_client_renderer_folder(self) -> None:
        budget = json.loads(SOURCE_BUDGET.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            budget_path = Path(tmp) / "presupuesto.json"
            html_path = Path(tmp) / "index.html"
            budget_path.write_text(json.dumps(budget), encoding="utf-8")

            render(budget_path, output_path=html_path)
            html = html_path.read_text(encoding="utf-8")

            self.assertTrue((Path(tmp) / "js" / "app.js").exists())
            self.assertTrue((Path(tmp) / "css" / "print.css").exists())
            self.assertTrue((Path(tmp) / "templates" / "body.html").exists())
            self.assertTrue((Path(tmp) / "presupuesto.json").exists())
            self.assertIn('id="document-root"', html)
            self.assertIn('id="measure-root"', html)
            self.assertIn('onclick="window.print()"', html)
            self.assertIn('src="js/app.js"', html)
            self.assertIn('href="css/print.css"', html)


class CatalogImportTest(unittest.TestCase):
    def test_import_csv_rows_appends_normalized_seed_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "catalog.csv"
            target = Path(tmp) / "services.csv"
            source.write_text(
                "sku,category,description,unit,unit_price,currency,source,updated_at,tags\n"
                "SVC-TDD,prueba,Servicio TDD,gl,123.45,DOP,test,2026-05-28,tdd\n",
                encoding="utf-8",
            )

            count = import_csv_rows(source, target)

            self.assertEqual(count, 1)
            self.assertIn("SVC-TDD", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
