#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import shutil
import urllib.request
from pathlib import Path
from typing import Any

from common import COMPANIES, OUTPUT, ROOT, load_json, normalize_company

DEFAULT_LOGO_SRC = "assets/logo.png"
STATIC = ROOT / "static"
SOURCE_LOGO = Path("/home/osmarg/Nextcloud/Calculos/bess punta catalina integra/construcosto/assets/logo.png")

CLIENT_INDEX = """<!doctype html>
<html lang=\"es\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Presupuesto</title>
    <link rel=\"icon\" type=\"image/png\" href=\"assets/logo.png\" />
    <link rel=\"stylesheet\" href=\"css/print.css\" />
  </head>
  <body>
    <div class=\"screen-toolbar\" aria-label=\"Controles de documento\">
      <div>
        <strong>Presupuesto</strong>
        <span id=\"render-status\">Cargando...</span>
      </div>
      <button type=\"button\" onclick=\"window.print()\">Imprimir / Guardar PDF</button>
    </div>

    <main id=\"document-root\" class=\"document-root\" aria-live=\"polite\"></main>
    <div id=\"measure-root\" class=\"measure-root\" aria-hidden=\"true\"></div>

    <script src=\"js/app.js\"></script>
  </body>
</html>
"""

UNIT_GLOSSARY = {
    "gl": ("Global / partida alzada", "Alcance completo que no se mide por longitud, área, volumen o unidad individual."),
    "m2": ("Metro cuadrado", "Áreas de piso, techo, pintura, cerámica, replanteo o terminaciones."),
    "m2-eq": ("Metro cuadrado equivalente", "Área convertida a condición equivalente de trabajo."),
    "m3": ("Metro cúbico", "Volúmenes de excavación, relleno, hormigón o material."),
    "m3-km": ("Metro cúbico-kilómetro", "Acarreo o transporte medido por volumen y distancia."),
    "m3c": ("Metro cúbico compactado", "Relleno regado, nivelado y compactado."),
    "ml": ("Metro lineal", "Elementos medidos por longitud, como drenajes o tuberías."),
    "m": ("Metro", "Elementos medidos por longitud."),
    "p2": ("Pie cuadrado", "Área comercial de ventanas, puertas de aluminio y vidrios."),
    "pl": ("Pie lineal", "Cables o conductores medidos por longitud."),
    "qq": ("Quintal", "Peso de acero de refuerzo."),
    "rollo": ("Rollo", "Material suministrado comercialmente por rollo."),
    "und": ("Unidad", "Piezas, equipos, accesorios o elementos contables individualmente."),
    "jornal": ("Jornal", "Jornada de mano de obra."),
}


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def render_template(template: str, data: dict[str, Any]) -> str:
    rendered = template
    for key, value in data.items():
        rendered = rendered.replace("{{" + key + "}}", str(value)).replace("{{ " + key + " }}", str(value))
    return rendered


def currency_info(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {"base": raw.get("base", "DOP"), "symbol": raw.get("symbol", raw.get("base", "DOP")), **raw}
    code = str(raw or "DOP")
    return {"base": code, "symbol": "RD$" if code == "DOP" else code}


def format_money(value: float, currency: dict[str, Any]) -> str:
    symbol = currency.get("symbol") or currency.get("base") or "DOP"
    return f"{symbol} {float(value or 0):,.2f}"


def format_usd(value: float, currency: dict[str, Any]) -> str:
    rate = float(currency.get("usdRate") or 0)
    return "US$ 0.00" if rate == 0 else f"US$ {float(value or 0) / rate:,.2f}"


def calculate_budget(raw: dict[str, Any]) -> dict[str, Any]:
    currency = currency_info(raw.get("currency"))
    partidas = []
    for partida in raw.get("partidas", []):
        subcategories = []
        for subcategory in partida.get("subcategories", []):
            items = []
            for item in subcategory.get("items", []):
                quantity = float(item.get("quantity") or 0)
                unit_price = float(item.get("unitPrice", item.get("unit_price", 0)) or 0)
                total = float(item.get("total", quantity * unit_price) or 0)
                normalized = {**item, "quantity": quantity, "unitPrice": unit_price, "total": total}
                items.append(normalized)
            subtotal = sum(float(item["total"]) for item in items)
            subcategories.append({**subcategory, "items": items, "subtotal": subtotal})
        total = sum(float(subcategory["subtotal"]) for subcategory in subcategories)
        partidas.append({**partida, "subcategories": subcategories, "total": total})

    subtotal_partidas = sum(float(partida["total"]) for partida in partidas)
    indirectos = []
    for indirecto in raw.get("indirectos", []):
        kind = indirecto.get("type", "percent")
        value = float(indirecto.get("value") or 0)
        amount = value if kind == "fixed" else subtotal_partidas * value / 100
        type_label = "Monto fijo" if kind == "fixed" else f"{value:.2f}%"
        indirectos.append({**indirecto, "type": kind, "value": value, "amount": amount, "typeLabel": type_label})
    total_indirectos = sum(float(indirecto["amount"]) for indirecto in indirectos)
    itbis_percent = float(raw.get("taxes", {}).get("itbisPercent", 18))
    base_itbis = subtotal_partidas + total_indirectos
    itbis = base_itbis * itbis_percent / 100
    return {
        **raw,
        "currency": currency,
        "partidas": partidas,
        "indirectos": indirectos,
        "totals": {
            "subtotalPartidas": subtotal_partidas,
            "totalIndirectos": total_indirectos,
            "itbisPercent": itbis_percent,
            "baseItbis": base_itbis,
            "itbis": itbis,
            "totalGeneral": base_itbis + itbis,
        },
    }


def render_subcategory(subcategory: dict[str, Any], currency: dict[str, Any]) -> str:
    rows = []
    for item in subcategory.get("items", []):
        rows.append(
            "<tr>"
            f"<td class=\"text-center\">{esc(item.get('code'))}</td>"
            f"<td>{esc(item.get('description'))}</td>"
            f"<td class=\"text-center\">{esc(item.get('unit'))}</td>"
            f"<td class=\"text-right\">{float(item.get('quantity') or 0):,.2f}</td>"
            f"<td class=\"text-right\">{format_money(float(item.get('unitPrice') or 0), currency)}</td>"
            f"<td class=\"text-right\">{format_money(float(item.get('total') or 0), currency)}</td>"
            "</tr>"
        )
    return f"""
    <section class="subcategory" data-subcategory-code="{esc(subcategory.get('code'))}">
      <div class="subcategory-title"><span>{esc(subcategory.get('code'))} {esc(subcategory.get('title'))}</span><span>{format_money(float(subcategory.get('subtotal') or 0), currency)}</span></div>
      <table class="budget-table"><thead><tr><th>Código</th><th>Descripción</th><th>Und.</th><th class="text-right">Cant.</th><th class="text-right">P. unit.</th><th class="text-right">Total</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
      <div class="subtotal-row"><span>Subtotal</span><span>{format_money(float(subcategory.get('subtotal') or 0), currency)}</span></div>
    </section>"""


def load_templates() -> dict[str, str]:
    names = ["body", "header", "footer", "partida", "subtotal_partidas", "indirecto", "total", "moneda_alt", "notas-consideraciones", "glosario-unidades"]
    return {name: (ROOT / "templates" / f"{name}.html").read_text(encoding="utf-8") for name in names}


def render_partida(partida: dict[str, Any], templates: dict[str, str], currency: dict[str, Any]) -> str:
    subcategories = "".join(render_subcategory(sub, currency) for sub in partida.get("subcategories", []))
    return render_template(templates["partida"], {
        "code": esc(partida.get("code")),
        "title": esc(partida.get("title")),
        "description": esc(partida.get("description")),
        "subcategories": subcategories,
        "totalFormatted": format_money(float(partida.get("total") or 0), currency),
    })


def render_summary_blocks(budget: dict[str, Any], templates: dict[str, str]) -> list[str]:
    currency = budget["currency"]
    totals = budget["totals"]
    indirect_rows = "".join(
        f"<tr><td>{esc(ind.get('name'))}</td><td class=\"text-right\">{format_money(totals['subtotalPartidas'], currency)}</td><td class=\"text-right\">{esc(ind.get('typeLabel'))}</td><td class=\"text-right\">{format_money(ind.get('amount'), currency)}</td></tr>"
        for ind in budget.get("indirectos", [])
    )
    blocks = [
        render_template(templates["subtotal_partidas"], {"subtotalPartidasFormatted": format_money(totals["subtotalPartidas"], currency)}),
        render_template(templates["indirecto"], {"rows": indirect_rows, "totalIndirectosFormatted": format_money(totals["totalIndirectos"], currency)}),
        render_template(templates["total"], {
            "subtotalPartidasFormatted": format_money(totals["subtotalPartidas"], currency),
            "totalIndirectosFormatted": format_money(totals["totalIndirectos"], currency),
            "baseItbisFormatted": format_money(totals["baseItbis"], currency),
            "itbisPercent": f"{totals['itbisPercent']:,.2f}",
            "itbisFormatted": format_money(totals["itbis"], currency),
            "totalGeneralFormatted": format_money(totals["totalGeneral"], currency),
        }),
    ]
    if currency.get("showUsdConversion") and float(currency.get("usdRate") or 0):
        blocks.append(render_template(templates["moneda_alt"], {
            "exchangeRate": f"1 USD = {float(currency['usdRate']):,.2f} {esc(currency.get('base', 'DOP'))}",
            "subtotalPartidasAlt": format_usd(totals["subtotalPartidas"], currency),
            "totalIndirectosAlt": format_usd(totals["totalIndirectos"], currency),
            "baseItbisAlt": format_usd(totals["baseItbis"], currency),
            "itbisPercent": f"{totals['itbisPercent']:,.2f}",
            "itbisAlt": format_usd(totals["itbis"], currency),
            "totalGeneralAlt": format_usd(totals["totalGeneral"], currency),
        }))
    return blocks


def notes_list(notes: list[Any]) -> str:
    return "<ul class=\"notes-list\">" + "".join(f"<li>{esc(note)}</li>" for note in notes) + "</ul>"


def render_notes_blocks(budget: dict[str, Any], templates: dict[str, str]) -> list[str]:
    general = budget.get("consideraciones", {}).get("generales", [])
    partidas = [p for p in budget.get("partidas", []) if p.get("consideraciones")]
    if not general and not partidas:
        return []
    partida_notes = "".join(f"<article class=\"notes-partida\"><h4>{esc(p.get('code'))}. {esc(p.get('title'))}</h4>{notes_list(p.get('consideraciones', []))}</article>" for p in partidas)
    return [render_template(templates["notas-consideraciones"], {
        "generalNotes": notes_list(general) if general else '<p class="notes-empty">Sin consideraciones generales.</p>',
        "partidaNotes": partida_notes or '<p class="notes-empty">Sin consideraciones por partida.</p>',
    })]


def render_glossary(budget: dict[str, Any], templates: dict[str, str]) -> str:
    units = sorted({str(item.get("unit")) for p in budget.get("partidas", []) for s in p.get("subcategories", []) for item in s.get("items", []) if item.get("unit")})
    rows = []
    for unit in units:
        label, usage = UNIT_GLOSSARY.get(unit, ("Unidad usada en el presupuesto", "Ver descripción de la partida correspondiente."))
        rows.append(f"<tr><td>{esc(unit)}</td><td>{esc(label)}</td><td>{esc(usage)}</td></tr>")
    return render_template(templates["glosario-unidades"], {"rows": "".join(rows)}) if rows else ""


def select_company(data: dict[str, Any], company_arg: str | None) -> str:
    candidates = [company_arg, data.get("company"), data.get("metadata", {}).get("company"), data.get("project", {}).get("client")]
    for candidate in candidates:
        if not candidate:
            continue
        value = str(candidate).strip().lower()
        if value in COMPANIES:
            return normalize_company(value)
    return "orgm"


def logo_src(company: str, output_dir: Path) -> str:
    info = COMPANIES[company]
    url = info.get("logo_url", "")
    if not url:
        return ""
    suffix = Path(url).suffix or ".png"
    asset = ROOT / "assets" / f"{company}{suffix}"
    output_asset = output_dir / asset.name
    if not asset.exists():
        try:
            asset.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, asset)
        except Exception as exc:
            close = getattr(exc, "close", None)
            if callable(close):
                close()
            return url
    if asset.exists():
        shutil.copy2(asset, output_asset)
        return asset.name
    return url


def page_shell(content: str, templates: dict[str, str], budget: dict[str, Any], company: str, page_number: int, page_count: int, logo: str) -> str:
    project = budget.get("project", {})
    header = render_template(templates["header"], {
        "logoSrc": esc(logo),
        "companyName": esc(COMPANIES[company]["name"]),
        "documentTitle": esc(project.get("documentTitle", "Presupuesto")),
        "projectName": esc(project.get("name", "")),
        "voltage": esc(project.get("voltage", "")),
        "location": esc(project.get("location", "")),
        "client": esc(project.get("client", budget.get("client", {}).get("name", ""))),
        "date": esc(project.get("date", budget.get("created_at", ""))),
        "revision": esc(project.get("revision", "")),
        "currencyBase": esc(budget.get("currency", {}).get("base", "DOP")),
    })
    footer = render_template(templates["footer"], {"companyName": esc(COMPANIES[company]["name"]), "pageNumber": page_number, "pageCount": page_count})
    return render_template(templates["body"], {"header": header, "content": content, "footer": footer})


def copy_tree_files(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        if path.is_file():
            shutil.copy2(path, target / path.name)


def prepare_client_renderer(presupuesto_path: Path, output_path: Path = OUTPUT / "index.html") -> Path:
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "js").mkdir(exist_ok=True)
    (output_dir / "css").mkdir(exist_ok=True)
    (output_dir / "templates").mkdir(exist_ok=True)
    (output_dir / "assets").mkdir(exist_ok=True)

    shutil.copy2(STATIC / "app.js", output_dir / "js" / "app.js")
    shutil.copy2(STATIC / "css" / "print.css", output_dir / "css" / "print.css")
    copy_tree_files(ROOT / "templates", output_dir / "templates")
    target_budget = output_dir / "presupuesto.json"
    if presupuesto_path.resolve() != target_budget.resolve():
        shutil.copy2(presupuesto_path, target_budget)
    if SOURCE_LOGO.exists():
        shutil.copy2(SOURCE_LOGO, output_dir / "assets" / "logo.png")
    output_path.write_text(CLIENT_INDEX, encoding="utf-8")
    return output_path


def render_static(presupuesto_path: Path, company_arg: str | None = None, output_path: Path = OUTPUT / "index.html") -> Path:
    raw = load_json(presupuesto_path)
    company = select_company(raw, company_arg)
    budget = calculate_budget({**raw, "company": company})
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    templates = load_templates()
    shutil.copy2(ROOT / "themes" / str(COMPANIES[company]["theme"]), output_dir / "theme.css")
    if company != "integra":
        shutil.copy2(ROOT / "themes" / "integra.css", output_dir / "integra.css")
    logo = logo_src(company, output_dir)

    blocks = [render_partida(p, templates, budget["currency"]) for p in budget.get("partidas", [])]
    blocks.extend(render_summary_blocks(budget, templates))
    blocks.extend(render_notes_blocks(budget, templates))
    glossary = render_glossary(budget, templates)
    if glossary:
        blocks.append(glossary)
    page_count = max(1, len(blocks))
    pages = "\n".join(page_shell(block, templates, budget, company, index + 1, page_count, logo) for index, block in enumerate(blocks or [""]))
    html_text = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(budget.get('project', {}).get('documentTitle', 'Presupuesto'))} - {esc(budget.get('project', {}).get('name', 'Proyecto'))}</title>
  <link rel="stylesheet" href="theme.css">
</head>
<body>
  <main class="document-root">{pages}</main>
</body>
</html>
"""
    output_path.write_text(html_text, encoding="utf-8")
    return output_path


def render(presupuesto_path: Path, company_arg: str | None = None, output_path: Path = OUTPUT / "index.html", static_fallback: bool = False) -> Path:
    if static_fallback:
        return render_static(presupuesto_path, company_arg, output_path)
    return prepare_client_renderer(presupuesto_path, output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render presupuesto HTML")
    parser.add_argument("presupuesto", type=Path)
    parser.add_argument("--company", choices=sorted(COMPANIES), default=None)
    parser.add_argument("--output", type=Path, default=OUTPUT / "index.html")
    parser.add_argument("--static-fallback", action="store_true", help="write legacy server-rendered single HTML instead of client renderer folder")
    args = parser.parse_args()
    path = render(args.presupuesto, args.company, args.output, static_fallback=args.static_fallback)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
