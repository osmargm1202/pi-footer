#!/usr/bin/env python3
from __future__ import annotations

import argparse
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from common import OUTPUT, load_json, normalize_company, write_json
from search_items import search
from render_html import calculate_budget


def money(value: float) -> float:
    return round(float(value or 0) + 0.0000001, 2)


def normalize_currency(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        base = str(raw.get("base", "DOP"))
        return {
            "base": base,
            "symbol": raw.get("symbol", "RD$" if base == "DOP" else base),
            "usdRate": float(raw.get("usdRate", 0) or 0),
            "showUsdConversion": bool(raw.get("showUsdConversion", False)),
            **raw,
        }
    code = str(raw or "DOP")
    return {"base": code, "symbol": "RD$" if code == "DOP" else code, "usdRate": 0, "showUsdConversion": False}


def normalize_taxes(request: dict[str, Any]) -> dict[str, Any]:
    if isinstance(request.get("taxes"), dict):
        return {"itbisPercent": float(request["taxes"].get("itbisPercent", 18))}
    return {"itbisPercent": float(request.get("itbisPercent", request.get("tax_rate", 0)) or 0) * (100 if float(request.get("tax_rate", 0) or 0) <= 1 else 1)}


def is_quote_match(match: dict[str, Any]) -> bool:
    return str(match.get("domain", "")).lower() == "cotizaciones" or str(match.get("sku", "")).startswith("COT-")


def same_price(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return money(float(left.get("unit_price", 0) or 0)) == money(float(right.get("unit_price", 0) or 0))


def normalized_text(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).casefold().split())


def same_concept(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return normalized_text(left.get("description")) == normalized_text(right.get("description")) and normalized_text(left.get("unit")) == normalized_text(right.get("unit"))


def find_price_conflict(matches: list[dict[str, Any]]) -> dict[str, dict[str, Any]] | None:
    quotes = [match for match in matches if is_quote_match(match)]
    catalogs = [match for match in matches if not is_quote_match(match)]
    for quote in quotes:
        for catalog in catalogs:
            if str(quote.get("source")) != str(catalog.get("source")) and same_concept(quote, catalog) and not same_price(quote, catalog):
                return {"quote": quote, "catalog": catalog}
    return None


def choose_conflict_match(requested: str, quote: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    print(f'Precio distinto para "{requested}"')
    print(f"1) Cotización: {quote.get('currency', 'DOP')} {money(float(quote.get('unit_price', 0) or 0))} - {quote.get('source')} - {quote.get('updated_at')}")
    print(f"2) Catálogo: {catalog.get('currency', 'DOP')} {money(float(catalog.get('unit_price', 0) or 0))} - {catalog.get('source')} - {catalog.get('updated_at')}")
    while True:
        choice = input("Usar [1/2]? ").strip()
        if choice == "1":
            return quote
        if choice == "2":
            return catalog
        print("Respuesta inválida. Escribe 1 o 2.")


def matched_item(raw: dict[str, Any], index_code: str) -> dict[str, Any]:
    requested = str(raw.get("description", "")).strip()
    quantity = float(raw.get("quantity", 1) or 0)
    matches = search(requested, 5) if requested else []
    conflict = find_price_conflict(matches)
    if conflict and "unitPrice" not in raw and "unit_price" not in raw:
        chosen = choose_conflict_match(requested, conflict["quote"], conflict["catalog"])
        matches = [chosen, *[match for match in matches if match.get("sku") != chosen.get("sku")]]
    if matches and "unitPrice" not in raw and "unit_price" not in raw:
        match = matches[0]
        description = str(match["description"])
        unit = str(match["unit"])
        unit_price = float(match["unit_price"])
        source_id = str(match.get("sku", ""))
        basis = f"{match.get('source', 'catalogo')}: {requested}" if requested else str(match.get("source", "catalogo"))
    else:
        match = matches[0] if matches else {}
        description = requested or str(raw.get("name", "Concepto sin descripción"))
        unit = str(raw.get("unit", match.get("unit", "gl")))
        unit_price = float(raw.get("unitPrice", raw.get("unit_price", match.get("unit_price", 0))) or 0)
        source_id = str(raw.get("sourceId", match.get("sku", "MANUAL")))
        basis = str(raw.get("basis", "Asignación manual preliminar"))
    return {
        "code": str(raw.get("code", index_code)),
        "description": description,
        "unit": unit,
        "quantity": quantity,
        "unitPrice": money(unit_price),
        "sourceId": source_id,
        "basis": basis,
    }


def partidas_from_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(items, start=1):
        partida_title = str(raw.get("partida", raw.get("category", "Partida general")))
        sub_title = str(raw.get("subcategory", raw.get("subcategoria", "Conceptos")))
        partida = buckets.setdefault(partida_title, {"title": partida_title, "description": raw.get("partida_description", ""), "sub": {}})
        sub = partida["sub"].setdefault(sub_title, {"title": sub_title, "items": []})
        sub["items"].append(raw)

    partidas = []
    for p_index, pdata in enumerate(buckets.values(), start=1):
        subcategories = []
        for s_index, sdata in enumerate(pdata["sub"].values(), start=1):
            code = f"{p_index}.{s_index}"
            items_out = [matched_item(raw, f"{code}.{i}") for i, raw in enumerate(sdata["items"], start=1)]
            subcategories.append({"code": code, "title": sdata["title"], "items": items_out})
        partidas.append({
            "code": str(p_index),
            "title": pdata["title"],
            "description": pdata.get("description") or f"Renglones agrupados en {pdata['title']}.",
            "subcategories": subcategories,
            "consideraciones": [],
        })
    return partidas


def normalize_existing_partidas(partidas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for p_index, partida in enumerate(partidas, start=1):
        subcategories = []
        for s_index, subcategory in enumerate(partida.get("subcategories", []), start=1):
            sub_code = str(subcategory.get("code", f"{p_index}.{s_index}"))
            items = [matched_item(item, f"{sub_code}.{i}") for i, item in enumerate(subcategory.get("items", []), start=1)]
            subcategories.append({**subcategory, "code": sub_code, "items": items})
        output.append({**partida, "code": str(partida.get("code", p_index)), "subcategories": subcategories})
    return output


def generate(request_path: Path, output_path: Path = OUTPUT / "presupuesto.json") -> dict[str, Any]:
    request = load_json(request_path)
    company = normalize_company(request.get("company") or request.get("metadata", {}).get("company"))
    today = date.today()
    valid_days = int(request.get("valid_days", 15))
    project = {
        "name": "Proyecto sin nombre",
        "documentTitle": "Presupuesto de construcción",
        "revision": "Rev. 0",
        "date": today.isoformat(),
        **request.get("project", {}),
    }
    if request.get("client", {}).get("name") and "client" not in project:
        project["client"] = request["client"]["name"]

    partidas = normalize_existing_partidas(request.get("partidas", [])) if request.get("partidas") else partidas_from_items(request.get("items", []))
    consideraciones = request.get("consideraciones") or {"generales": request.get("notes", [])}
    presupuesto = {
        "company": company,
        "project": project,
        "currency": normalize_currency(request.get("currency")),
        "taxes": normalize_taxes(request),
        "metadata": {
            "company": company,
            "created_at": today.isoformat(),
            "valid_until": (today + timedelta(days=valid_days)).isoformat(),
            "sourceDocument": str(request_path),
            "status": request.get("status", "borrador"),
            "notes": request.get("metadata", {}).get("notes", []),
            **request.get("metadata", {}),
        },
        "partidas": partidas,
        "indirectos": request.get("indirectos", []),
        "consideraciones": consideraciones,
    }
    calculated = calculate_budget(presupuesto)
    presupuesto["totals"] = calculated["totals"]
    write_json(output_path, presupuesto)
    return presupuesto


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate output/presupuesto.json")
    parser.add_argument("request", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT / "presupuesto.json")
    args = parser.parse_args()
    presupuesto = generate(args.request, args.output)
    count = sum(len(sub.get("items", [])) for partida in presupuesto["partidas"] for sub in partida.get("subcategories", []))
    print(f"wrote {args.output} with {count} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
