#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import unicodedata
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

from common import DOMAINS, SEED

REQUIRED = ["sku", "category", "description", "unit", "unit_price", "currency", "source", "updated_at", "tags"]
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

WORKBOOKS = {
    "materials": "Materiales e Insumos Santo Domingo ConstruCosto.do MAYO26.xlsx",
    "labor": "Mano de obra Santo Domingo ConstruCosto.do MAYO26.xlsx",
    "equipment_earthworks": "Equipos y Movimientos de Tierra Santo Domingo ConstruCosto.do MAYO26.xlsx",
    "services": "Analisis de Costos Santo Domingo ConstruCosto.do MAYO26.xlsx",
}

SOURCE_LABELS = {
    "materials": "ConstruCosto.do Materiales e Insumos Santo Domingo MAYO26",
    "labor": "ConstruCosto.do Mano de Obra Santo Domingo MAYO26",
    "equipment": "ConstruCosto.do Equipos y Movimientos de Tierra Santo Domingo MAYO26",
    "earthworks": "ConstruCosto.do Equipos y Movimientos de Tierra Santo Domingo MAYO26",
    "services": "seed-services-local",
}

PREFIXES = {
    "materials": "MAT",
    "labor": "LAB",
    "equipment": "EQP",
    "earthworks": "TER",
    "services": "SER",
}


def _column_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        return 0
    value = 0
    for char in match.group(1):
        value = value * 26 + ord(char) - 64
    return value - 1


def _cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    value_node = cell.find(f"{NS}v")
    if value_node is None or value_node.text is None:
        return ""
    value = value_node.text.strip()
    if cell.attrib.get("t") == "s" and value:
        return shared_strings[int(value)]
    return value


def read_xlsx_rows(path: Path) -> list[list[str]]:
    if not path.exists():
        raise SystemExit(f"source workbook not found: {path}")
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise SystemExit(f"not a readable .xlsx workbook: {path}") from exc
    with archive:
        names = set(archive.namelist())
        if "xl/worksheets/sheet1.xml" not in names:
            raise SystemExit(f"workbook has no first worksheet: {path}")
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall(f"{NS}si"):
                shared_strings.append("".join(node.text or "" for node in item.iter(f"{NS}t")))
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows: list[list[str]] = []
        for row in root.iter(f"{NS}row"):
            values: list[str] = []
            for cell in row.findall(f"{NS}c"):
                index = _column_index(cell.attrib.get("r", "A"))
                while len(values) <= index:
                    values.append("")
                values[index] = _cell_text(cell, shared_strings).strip()
            rows.append(values)
        return rows


def decimal_text(value: str) -> str:
    cleaned = (value or "").replace(",", "").strip()
    if cleaned in {"", "-"}:
        return ""
    try:
        number = Decimal(cleaned)
    except InvalidOperation:
        return ""
    if number < 0:
        return ""
    return format(number.quantize(Decimal("0.01")), "f")


def _text(value: str) -> str:
    return " ".join((value or "").split())


def _code_text(code: str) -> str:
    text = _text(code)
    if not text:
        return ""
    try:
        number = Decimal(text)
    except InvalidOperation:
        return text
    if number == number.to_integral():
        return str(int(number))
    rounded = number.quantize(Decimal("0.01"))
    normalized = format(rounded.normalize(), "f")
    return normalized.rstrip("0").rstrip(".")


def _ascii_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return _text(ascii_text)


def _ascii_slug(value: str) -> str:
    ascii_text = _ascii_text(value).replace("'", "").replace("\"", "")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_text.upper()).strip("-")
    return slug or "ROW"


def slugify_sku(domain: str, code: str, description: str) -> str:
    prefix = PREFIXES[domain]
    code_slug = _ascii_slug(_code_text(code)) if _code_text(code) else ""
    desc_slug = _ascii_slug(description)[:54].strip("-")
    if code_slug:
        return f"{prefix}-{code_slug}-{desc_slug}"[:80].rstrip("-")
    return f"{prefix}-{desc_slug}"[:80].rstrip("-")


def normalize_catalog_row(
    *,
    domain: str,
    code: str,
    category: str,
    description: str,
    unit: str,
    price: str,
    source: str,
    updated_at: str,
    supplier: str = "",
) -> dict[str, str] | None:
    description = _text(description)
    unit = _text(unit).upper()
    unit_price = decimal_text(price)
    if not description or not unit or not unit_price:
        return None
    category = _text(category) or "SIN CATEGORIA"
    tag_parts = [description, category, supplier, _code_text(code), _ascii_text(description), _ascii_text(category)]
    haystack = " ".join(tag_parts).lower()
    if domain == "labor" and ("maestro" in haystack or "trabajador" in haystack or "albanileria" in haystack):
        tag_parts.append("oficial mano obra jornales diarios")
    if domain in {"equipment", "earthworks", "materials"} and "retropala" in haystack:
        tag_parts.append("retroexcavadora")
    tags = _text(" ".join(part for part in tag_parts if part))
    return {
        "sku": slugify_sku(domain, code, description),
        "category": category,
        "description": description,
        "unit": unit,
        "unit_price": unit_price,
        "currency": "DOP",
        "source": source,
        "updated_at": updated_at,
        "tags": tags,
    }


def _is_category_row(code: str, description: str, unit: str, price: str) -> bool:
    code_text = _code_text(code)
    return bool(description and code_text and "." not in code_text and not unit and not decimal_text(price))


def extract_materials(path: Path, updated_at: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    category = ""
    for row in read_xlsx_rows(path)[1:]:
        cells = row + [""] * 7
        code, description, unit, _gross, net, notes, supplier = cells[:7]
        if description and not unit and not decimal_text(net):
            category = _text(description)
            continue
        normalized = normalize_catalog_row(
            domain="materials",
            code=code,
            category=category,
            description=description,
            unit=unit,
            price=net or _gross,
            source=SOURCE_LABELS["materials"],
            updated_at=updated_at,
            supplier=" ".join(part for part in [notes, supplier] if part),
        )
        if normalized:
            rows.append(normalized)
    return _dedupe(rows)


def extract_labor(path: Path, updated_at: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    category = "JORNALES DIARIOS"
    for row in read_xlsx_rows(path):
        cells = row + [""] * 12
        code, description, unit, price = cells[:4]
        if _text(description).upper() in {"DESCRIPCION", "BRIGADAS"}:
            continue
        if description and not unit and not decimal_text(price):
            category = _text(description)
            continue
        normalized = normalize_catalog_row(
            domain="labor",
            code=code,
            category=category,
            description=description,
            unit=unit,
            price=price,
            source=SOURCE_LABELS["labor"],
            updated_at=updated_at,
        )
        if normalized:
            rows.append(normalized)
    return _dedupe(rows)


def extract_equipment_and_earthworks(path: Path, updated_at: str) -> dict[str, list[dict[str, str]]]:
    extracted = {"equipment": [], "earthworks": []}
    domain = "equipment"
    category = ""
    for row in read_xlsx_rows(path):
        cells = row + [""] * 10
        code, description, _qty, unit, _pu, _itbis, subtotal, _subtotal_itbis, total, supplier = cells[:10]
        if _text(description).upper() == "DESCRIPCION":
            continue
        if _is_category_row(code, description, unit, total or subtotal):
            category = _text(description)
            if _code_text(code) != "100":
                domain = "earthworks"
            continue
        if not _code_text(code) or "." not in _code_text(code):
            continue
        normalized = normalize_catalog_row(
            domain=domain,
            code=code,
            category=category,
            description=description,
            unit=unit,
            price=subtotal or total,
            source=SOURCE_LABELS[domain],
            updated_at=updated_at,
            supplier=supplier,
        )
        if normalized:
            extracted[domain].append(normalized)
    return {key: _dedupe(value) for key, value in extracted.items()}


def _dedupe(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: dict[str, int] = {}
    output: list[dict[str, str]] = []
    for row in rows:
        sku = row["sku"]
        count = seen.get(sku, 0)
        seen[sku] = count + 1
        if count:
            row = dict(row)
            row["sku"] = f"{sku}-{count + 1}"[:80].rstrip("-")
        output.append(row)
    return output


def read_seed_domain(domain: str) -> list[dict[str, str]]:
    path = SEED / DOMAINS[domain]
    with path.open(newline="", encoding="utf-8") as handle:
        return [{name: row.get(name, "") for name in REQUIRED} for row in csv.DictReader(handle)]


def write_seed(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED)
        writer.writeheader()
        writer.writerows(rows)


def import_construcosto_catalogs(source_root: Path, output_seed_dir: Path, updated_at: str = "2026-05-01") -> dict[str, int]:
    source_root = source_root.expanduser().resolve()
    output_seed_dir.mkdir(parents=True, exist_ok=True)

    domain_rows: dict[str, list[dict[str, str]]] = {
        "materials": extract_materials(source_root / WORKBOOKS["materials"], updated_at),
        "labor": extract_labor(source_root / WORKBOOKS["labor"], updated_at),
    }
    domain_rows.update(extract_equipment_and_earthworks(source_root / WORKBOOKS["equipment_earthworks"], updated_at))
    for domain in ("services", "cotizaciones"):
        domain_rows[domain] = read_seed_domain(domain)

    counts: dict[str, int] = {}
    for domain in DOMAINS:
        rows = domain_rows[domain]
        write_seed(output_seed_dir / DOMAINS[domain], rows)
        counts[domain] = len(rows)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract ConstruCosto MAYO26 workbooks into normalized presupuesto seed CSVs")
    parser.add_argument("source_root", type=Path, help="folder containing ConstruCosto .xlsx workbooks")
    parser.add_argument("--output", type=Path, default=SEED, help="target seed CSV folder (default: data/seed)")
    parser.add_argument("--updated-at", default="2026-05-01", help="catalog date stored in seed rows")
    args = parser.parse_args()

    counts = import_construcosto_catalogs(args.source_root, args.output, args.updated_at)
    for domain in DOMAINS:
        print(f"{domain}: {counts[domain]} rows -> {args.output / DOMAINS[domain]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
