---
name: presupuesto-orgm
description: "Use this skill when creating, pricing, searching, rendering, or serving ORGM/Integra/DAPEC construction presupuesto budgets with local SQLite price data and printable HTML output."
---

# Presupuesto ORGM

Generate full `presupuesto.json` (`project`, `currency`, `taxes`, `metadata`, `partidas[].subcategories[].items[]`, `indirectos`, `consideraciones`) and printable A4 HTML from local seed price data.

## Use when

- User asks for a presupuesto, cotización, budget, construction estimate, catálogo de precios, or branded printable proposal.
- User needs local price search by material, labor, equipment, earthwork, or service.
- User wants ORGM, Integra, or DAPEC themed HTML.

## Workflow

Run commands from this directory unless path shown otherwise:

```bash
cd skills/presupuesto-orgm
python scripts/build_db.py
python scripts/search_items.py concreto
python scripts/import_catalog_csv.py /path/catalog.csv services
python scripts/generate_presupuesto.py docs/sample-request.json
python scripts/render_html.py output/presupuesto.json --company orgm
python scripts/serve_output.py --port 8765
```

1. Read `docs/budget-json.md`, `docs/database.md`, and `docs/themes.md`.
2. Build or refresh local DB with `scripts/build_db.py`.
3. Search items with `scripts/search_items.py "query text"` when mapping user scope to price rows.
4. Import real normalized CSV rows with `scripts/import_catalog_csv.py` when extending catalog/services, then rebuild DB.
5. Write request JSON using `docs/sample-request.json` shape; use either full `partidas[]` or simple `items[]` grouped by `partida`/`subcategory`.
6. Generate `output/presupuesto.json` with `scripts/generate_presupuesto.py`.
7. Render printable HTML with `scripts/render_html.py`; output includes totals, indirectos, ITBIS, alternate currency, notes/consideraciones, and unit glossary.
8. Treat everything in `output/` as disposable generated output.

## Company themes

- `orgm` default: ORGM colors and logo URL `https://r2.or-gm.com/orgm.png`.
- `integra`: dark blue and gold.
- `dapec`: technical green/blue and logo URL `https://r2.or-gm.com/dapec.png`.

## Catalog refresh

Bundled seed CSVs include extracted ConstruCosto MAYO26 rows. To refresh from local source workbooks without altering originals:

```bash
cd skills/presupuesto-orgm
python scripts/import_construcosto_workbooks.py "/home/osmarg/Nextcloud/Calculos/bess punta catalina integra/construcosto" --output data/seed
python scripts/build_db.py
```

Add custom service prices in `data/seed/services.csv`, then rebuild DB.

## Real quote refresh

Normalize supplier quote PDFs into searchable catalog rows:

```bash
cd skills/presupuesto-orgm
python scripts/import_cotizaciones_pdfs.py ../../cotizaciones_temp --output data/seed/cotizaciones_realizadas.csv
python scripts/build_db.py
```

Quote rows preserve supplier/date/file provenance. During budget generation, if a quote and catalog price differ for the same requested concept, ask the user which source to use.

## Safety

Catalog prices are extracted seeds, not final commercial guarantees. Confirm quantities, taxes, currency, exclusions, validity dates, and current market prices before sharing final documents.
