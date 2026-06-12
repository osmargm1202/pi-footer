from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from common import DOMAINS  # noqa: E402
from import_construcosto_workbooks import (  # noqa: E402
    import_construcosto_catalogs,
    normalize_catalog_row,
    slugify_sku,
)

SOURCE_ROOT = Path("/home/osmarg/Nextcloud/Calculos/bess punta catalina integra/construcosto")
SEED_ROOT = SKILL_ROOT / "data" / "seed"


class CatalogWorkbookImportTest(unittest.TestCase):
    def test_slugify_sku_is_stable_ascii_and_domain_prefixed(self) -> None:
        self.assertEqual(slugify_sku("materials", "100.02000000000001", "Cal Hidratada 20 kilos"), "MAT-100-02-CAL-HIDRATADA-20-KILOS")
        self.assertEqual(slugify_sku("labor", "", "Peón o Trabajador No Calificado (PE)"), "LAB-PEON-O-TRABAJADOR-NO-CALIFICADO-PE")

    def test_normalize_catalog_row_keeps_numeric_price_and_search_tags(self) -> None:
        row = normalize_catalog_row(
            domain="materials",
            code="",
            category="CEMENTOS",
            description="Cal Grande hidratada 20 kilos",
            unit="FDA",
            price="419.49",
            source="ConstruCosto.do Materiales MAYO26",
            updated_at="2026-05-01",
            supplier="MINIBANNER CON LINK",
        )

        self.assertEqual(row["sku"], "MAT-CAL-GRANDE-HIDRATADA-20-KILOS")
        self.assertEqual(row["category"], "CEMENTOS")
        self.assertEqual(row["unit_price"], "419.49")
        self.assertEqual(row["currency"], "DOP")
        self.assertIn("Cal Grande hidratada", row["tags"])
        self.assertIn("MINIBANNER", row["tags"])

    def test_normalize_catalog_row_adds_ascii_and_domain_search_aliases(self) -> None:
        labor = normalize_catalog_row(
            domain="labor",
            code="",
            category="JORNALES DIARIOS",
            description="Maestro (MA)",
            unit="DIA",
            price="2941.78",
            source="ConstruCosto.do Mano de Obra MAYO26",
            updated_at="2026-05-01",
        )
        equipment = normalize_catalog_row(
            domain="equipment",
            code="100.03",
            category="COSTOS HORARIOS MAQUINARIAS",
            description="RETROPALA CAT416E O SIMILAR",
            unit="HR",
            price="3176.44",
            source="ConstruCosto.do Equipos MAYO26",
            updated_at="2026-05-01",
        )

        self.assertIn("oficial", labor["tags"])
        self.assertIn("jornales diarios", labor["tags"])
        self.assertIn("retroexcavadora", equipment["tags"])

    def test_source_workbooks_extract_minimum_real_row_counts(self) -> None:
        if not SOURCE_ROOT.exists():
            self.skipTest(f"source catalog folder unavailable: {SOURCE_ROOT}")
        with tempfile.TemporaryDirectory() as tmp:
            counts = import_construcosto_catalogs(SOURCE_ROOT, Path(tmp))

            self.assertGreaterEqual(counts["materials"], 100)
            self.assertGreaterEqual(counts["labor"], 100)
            self.assertGreaterEqual(counts["equipment"], 10)
            self.assertGreaterEqual(counts["earthworks"], 10)
            self.assertGreaterEqual(counts["services"], 3)
            self.assertGreaterEqual(counts["cotizaciones"], 1)

    def test_bundled_seed_csvs_have_real_minimum_row_counts(self) -> None:
        expected = {"materials": 100, "labor": 100, "equipment": 10, "earthworks": 10, "services": 3, "cotizaciones": 1}
        passthrough_domains = {"services", "cotizaciones"}
        for domain, minimum in expected.items():
            with self.subTest(domain=domain):
                with (SEED_ROOT / DOMAINS[domain]).open(newline="", encoding="utf-8") as handle:
                    rows = list(csv.DictReader(handle))
                self.assertGreaterEqual(len(rows), minimum)
                self.assertTrue(all(row["source"].startswith("ConstruCosto.do") or domain in passthrough_domains for row in rows))


if __name__ == "__main__":
    unittest.main()
