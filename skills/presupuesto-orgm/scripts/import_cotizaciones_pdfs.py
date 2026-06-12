#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from import_catalog_csv import REQUIRED


@dataclass(frozen=True)
class CotizacionRow:
    sku: str
    category: str
    description: str
    unit: str
    unit_price: str
    currency: str
    source: str
    updated_at: str
    tags: str
    supplier: str
    source_file: str


def ascii_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", normalized.upper()).strip("-")
    return slug or "SIN-DESCRIPCION"


def slugify_quote_sku(supplier: str, updated_at: str, description: str) -> str:
    base = f"COT-{ascii_slug(supplier)[:32]}-{updated_at}-{ascii_slug(description)[:72]}"
    return base.rstrip("-")


def parse_date(value: str) -> str:
    value = value.strip()
    patterns = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"]
    for pattern in patterns:
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            pass
    return value


def detect_supplier(text: str, source_file: str) -> str:
    patterns = [
        r"SUPLIDOR\s*[:\-]\s*(.+)",
        r"Proveedor\s*[:\-]\s*(.+)",
        r"Cliente\s*[:\-]\s*(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                return re.sub(r"\s+", " ", value)[:80]
    return Path(source_file).stem.strip()[:80] or "SUPLIDOR DESCONOCIDO"


def detect_date(text: str) -> str:
    patterns = [
        r"Fecha\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_date(match.group(1))
    return "1900-01-01"


def normalize_price(raw: str) -> str:
    cleaned = raw.replace("RD$", "").replace("US$", "").replace("$", "")
    cleaned = cleaned.replace(",", "").strip()
    value = float(cleaned)
    return f"{value:.2f}"


def detect_currency(line: str) -> str:
    upper = line.upper()
    if "US$" in upper or "USD" in upper:
        return "USD"
    return "DOP"


MONEY_PATTERN = r"(?:RD\$|US\$|\$)?\s*\d[\d,]*\.\d{2}"
SUMMARY_PREFIXES = ("DESCUENTO", "SUBTOTAL", "TOTAL", "ITBIS", "IMPUESTO")


def parse_line_item(line: str) -> tuple[str, str, str, str] | None:
    stripped = line.strip()
    if not re.search(MONEY_PATTERN, stripped, flags=re.IGNORECASE):
        return None
    if stripped.upper().startswith(SUMMARY_PREFIXES):
        return None
    match = re.match(
        rf"^(?P<description>.+?)\s+(?P<quantity>\d+(?:\.\d+)?)\s+(?P<unit>[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9/]+)\s+(?P<price>{MONEY_PATTERN})(?:\s+{MONEY_PATTERN})?\s*$",
        stripped,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    description = re.sub(r"\s+", " ", match.group("description")).strip(" -")
    unit = match.group("unit").upper()
    price = normalize_price(match.group("price"))
    currency = detect_currency(line)
    if not description or len(description) < 3:
        return None
    return description, unit, price, currency


def parse_quote_text(text: str, source_file: str) -> list[CotizacionRow]:
    supplier = detect_supplier(text, source_file)
    updated_at = detect_date(text)
    rows: list[CotizacionRow] = []
    for raw_line in text.splitlines():
        parsed = parse_line_item(raw_line)
        if not parsed:
            continue
        description, unit, unit_price, currency = parsed
        sku = slugify_quote_sku(supplier, updated_at, description)
        source = f"Cotización {supplier} {source_file}"
        tags = " ".join([supplier, source_file, description, unit, "cotizacion"])
        if updated_at == "1900-01-01" or supplier == "SUPLIDOR DESCONOCIDO":
            tags += " needs-review"
        rows.append(CotizacionRow(
            sku=sku,
            category="cotizacion",
            description=description,
            unit=unit,
            unit_price=unit_price,
            currency=currency,
            source=source,
            updated_at=updated_at,
            tags=tags,
            supplier=supplier,
            source_file=source_file,
        ))
    return rows


def row_to_catalog_dict(row: CotizacionRow) -> dict[str, str]:
    return {name: getattr(row, name) for name in REQUIRED}


def write_quote_csv(rows: list[CotizacionRow], output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED)
        writer.writeheader()
        for row in rows:
            writer.writerow(row_to_catalog_dict(row))
    return len(rows)


def extract_text_from_pdf(path: Path) -> str:
    pdftotext = subprocess.run(
        ["bash", "-lc", "command -v pdftotext"],
        text=True,
        capture_output=True,
    ).stdout.strip()
    if pdftotext:
        result = subprocess.run([pdftotext, "-layout", str(path), "-"], text=True, capture_output=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ""
    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def import_pdf_folder(folder: Path, output: Path) -> tuple[int, list[str]]:
    rows: list[CotizacionRow] = []
    warnings: list[str] = []
    for pdf in sorted(folder.glob("*.pdf")):
        text = extract_text_from_pdf(pdf)
        if not text.strip():
            warnings.append(f"no text extracted: {pdf}")
            continue
        parsed = parse_quote_text(text, pdf.name)
        if not parsed:
            warnings.append(f"no price rows parsed: {pdf}")
            continue
        rows.extend(parsed)
    count = write_quote_csv(rows, output)
    return count, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract supplier quote PDFs into normalized cotizaciones_realizadas.csv")
    parser.add_argument("folder", type=Path, help="Folder containing quote PDFs")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "seed" / "cotizaciones_realizadas.csv")
    args = parser.parse_args()
    count, warnings = import_pdf_folder(args.folder, args.output)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(f"wrote {args.output} with {count} quote rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
