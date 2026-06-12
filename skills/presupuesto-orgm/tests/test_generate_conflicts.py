from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import generate_presupuesto  # noqa: E402


CATALOG_MATCH = {
    "sku": "MAT-GRUA-BASE",
    "domain": "equipment",
    "description": "Grúa telescópica",
    "unit": "HR",
    "unit_price": 4000.0,
    "currency": "DOP",
    "source": "ConstruCosto.do Equipos MAYO26",
    "updated_at": "2026-05-01",
    "tags": "grua",
}
QUOTE_MATCH = {
    "sku": "COT-TEST-2026-05-22-GRUA-TELESCOPICA",
    "domain": "cotizaciones",
    "description": "Grúa telescópica",
    "unit": "HR",
    "unit_price": 4500.0,
    "currency": "DOP",
    "source": "Cotización TEST fixture.pdf",
    "updated_at": "2026-05-22",
    "tags": "grua cotizacion",
}


class GenerateConflictTest(unittest.TestCase):
    def test_detects_conflict_between_quote_and_catalog_prices(self) -> None:
        conflict = generate_presupuesto.find_price_conflict([QUOTE_MATCH, CATALOG_MATCH])

        self.assertIsNotNone(conflict)
        self.assertEqual(conflict["quote"]["sku"], QUOTE_MATCH["sku"])
        self.assertEqual(conflict["catalog"]["sku"], CATALOG_MATCH["sku"])

    def test_ignores_unrelated_quote_and_catalog_matches(self) -> None:
        quote = {
            **QUOTE_MATCH,
            "description": "Transporte de equipo",
            "unit": "UND",
            "unit_price": 12000.0,
        }
        catalog = {
            **CATALOG_MATCH,
            "description": "Grúa telescópica",
            "unit": "HR",
            "unit_price": 4000.0,
        }

        conflict = generate_presupuesto.find_price_conflict([quote, catalog])

        self.assertIsNone(conflict)

    def test_user_can_choose_quote_price_for_conflict(self) -> None:
        with patch("builtins.input", return_value="1"):
            chosen = generate_presupuesto.choose_conflict_match("Grúa telescópica", QUOTE_MATCH, CATALOG_MATCH)

        self.assertEqual(chosen["sku"], QUOTE_MATCH["sku"])

    def test_user_can_choose_catalog_price_for_conflict(self) -> None:
        with patch("builtins.input", return_value="2"):
            chosen = generate_presupuesto.choose_conflict_match("Grúa telescópica", QUOTE_MATCH, CATALOG_MATCH)

        self.assertEqual(chosen["sku"], CATALOG_MATCH["sku"])

    def test_matched_item_uses_selected_quote_when_conflict_exists(self) -> None:
        with patch.object(generate_presupuesto, "search", return_value=[QUOTE_MATCH, CATALOG_MATCH]):
            with patch("builtins.input", return_value="1"):
                item = generate_presupuesto.matched_item({"description": "Grúa telescópica", "quantity": 2}, "1.1.1")

        self.assertEqual(item["unitPrice"], 4500.0)
        self.assertEqual(item["sourceId"], QUOTE_MATCH["sku"])
        self.assertIn("Cotización TEST", item["basis"])


if __name__ == "__main__":
    unittest.main()
