from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from import_cotizaciones_pdfs import (  # noqa: E402
    CotizacionRow,
    parse_quote_text,
    slugify_quote_sku,
    write_quote_csv,
)


SAMPLE_TEXT = """
SUPLIDOR: ALQUIMEDEZ
Fecha: 22/05/2026
Cotización No. 1234
Descripción                         Cant. Und   Precio
Alquiler retroexcavadora CAT416E       1  HR    RD$ 3,250.00
Transporte de equipo                   1  UND   RD$ 12,000.00
"""


class CotizacionesImportTest(unittest.TestCase):
    def test_slugify_quote_sku_is_stable_ascii_and_prefixed(self) -> None:
        sku = slugify_quote_sku("ALQUIMEDEZ", "2026-05-22", "Alquiler retroexcavadora CAT416E")
        self.assertEqual(sku, "COT-ALQUIMEDEZ-2026-05-22-ALQUILER-RETROEXCAVADORA-CAT416E")

    def test_parse_quote_text_extracts_supplier_date_and_prices(self) -> None:
        rows = parse_quote_text(SAMPLE_TEXT, source_file="ALQUIMEDEZ 22-5.pdf")

        self.assertEqual(len(rows), 2)
        first = rows[0]
        self.assertIsInstance(first, CotizacionRow)
        self.assertEqual(first.supplier, "ALQUIMEDEZ")
        self.assertEqual(first.updated_at, "2026-05-22")
        self.assertEqual(first.description, "Alquiler retroexcavadora CAT416E")
        self.assertEqual(first.unit, "HR")
        self.assertEqual(first.unit_price, "3250.00")
        self.assertEqual(first.currency, "DOP")
        self.assertEqual(first.source, "Cotización ALQUIMEDEZ ALQUIMEDEZ 22-5.pdf")
        self.assertIn("ALQUIMEDEZ", first.tags)
        self.assertIn("ALQUIMEDEZ 22-5.pdf", first.tags)

    def test_write_quote_csv_uses_catalog_columns(self) -> None:
        rows = parse_quote_text(SAMPLE_TEXT, source_file="ALQUIMEDEZ 22-5.pdf")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "cotizaciones_realizadas.csv"
            count = write_quote_csv(rows, output)

            self.assertEqual(count, 2)
            with output.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                data = list(reader)

        self.assertEqual(reader.fieldnames, [
            "sku", "category", "description", "unit", "unit_price", "currency", "source", "updated_at", "tags",
        ])
        self.assertTrue(data[0]["sku"].startswith("COT-ALQUIMEDEZ-2026-05-22"))
        self.assertEqual(data[0]["category"], "cotizacion")

    def test_quote_line_with_discount_uses_unit_price_not_line_total(self) -> None:
        text = """
SUPLIDOR: JJ
Fecha: 22/05/2026
CABLE URD #2 13.5 ML RD$ 357.00 RD$ 4,819.50
DESCUENTO 10% RD$ 481.95
TOTAL RD$ 4,337.55
"""

        rows = parse_quote_text(text, source_file="JJ.pdf")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].description, "CABLE URD #2")
        self.assertEqual(rows[0].unit, "ML")
        self.assertEqual(rows[0].unit_price, "357.00")

    def test_unparseable_price_is_not_invented_and_gets_needs_review(self) -> None:
        text = "SUPLIDOR: JOSE G\nFecha: 2026-05-20\nServicio sin precio claro UND consultar"

        rows = parse_quote_text(text, source_file="jose g.pdf")

        self.assertEqual(rows, [])


import sqlite3

from build_db import build  # noqa: E402
from common import DOMAINS  # noqa: E402


class CotizacionesDatabaseTest(unittest.TestCase):
    def test_cotizaciones_domain_is_registered(self) -> None:
        self.assertIn("cotizaciones", DOMAINS)
        self.assertEqual(DOMAINS["cotizaciones"], "cotizaciones_realizadas.csv")

    def test_build_db_loads_cotizaciones_into_price_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "presupuesto.db"
            total = build(db_path)
            conn = sqlite3.connect(db_path)
            try:
                row = conn.execute(
                    "SELECT sku, domain, source FROM price_items WHERE sku = ?",
                    ("COT-TEST-2026-05-22-GRUA-TELESCOPICA",),
                ).fetchone()
            finally:
                conn.close()

        self.assertGreater(total, 0)
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "cotizaciones")
        self.assertIn("Cotización TEST", row[2])


if __name__ == "__main__":
    unittest.main()
