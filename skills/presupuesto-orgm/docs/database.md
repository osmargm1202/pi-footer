# Database

`data/schema.sql` creates domain tables plus unified search tables:

- `materials`
- `labor`
- `equipment`
- `earthworks`
- `services`
- `price_items`
- `price_items_fts`

Build database:

```bash
python scripts/build_db.py
```

## Refresh bundled ConstruCosto catalogs

Source workbooks are not committed and must not be edited in place. When the ConstruCosto `.xlsx` files are available, regenerate normalized seed CSVs with:

```bash
python scripts/import_construcosto_workbooks.py \
  "/home/osmarg/Nextcloud/Calculos/bess punta catalina integra/construcosto" \
  --output data/seed
python scripts/build_db.py
```

The extractor reads workbook XML with Python stdlib, writes deterministic CSV columns, stores net DOP prices, and preserves current `data/seed/services.csv` so service prices remain manually extensible.

Current bundled seed sources:

- `materials.csv`: Materiales e Insumos Santo Domingo ConstruCosto.do MAYO26.xlsx
- `labor.csv`: Mano de obra Santo Domingo ConstruCosto.do MAYO26.xlsx
- `equipment.csv` and `earthworks.csv`: Equipos y Movimientos de Tierra Santo Domingo ConstruCosto.do MAYO26.xlsx
- `services.csv`: local extensible service seed rows

Search database:

```bash
python scripts/search_items.py "concreto"
python scripts/search_items.py "excavacion" --limit 3
```

Import normalized catalog rows into a seed domain:

```bash
python scripts/import_catalog_csv.py /path/catalog.csv services
python scripts/import_catalog_csv.py /path/catalog.csv materials --replace
python scripts/build_db.py
```

CSV columns:

```text
sku,category,description,unit,unit_price,currency,source,updated_at,tags
```

## Cotizaciones reales

Real supplier quote PDFs can be normalized into `data/seed/cotizaciones_realizadas.csv`:

```bash
python scripts/import_cotizaciones_pdfs.py ../../cotizaciones_temp --output data/seed/cotizaciones_realizadas.csv
python scripts/build_db.py
```

Rows use the same catalog columns as other domains. `source` must include supplier/file provenance, and `updated_at` must be the quote date. If a quote price conflicts with a catalog price during `generate_presupuesto.py`, the generator asks which source to use.

PDF extraction is best-effort. If text cannot be extracted or prices are unclear, the script reports warnings instead of inventing prices.

## Service extension

Add new service rows to `data/seed/services.csv` with stable `sku` values, source name/date in `source`/`updated_at`, and searchable terms in `tags`. Rebuild DB after import. For a new domain, add a table to `data/schema.sql`, add CSV file under `data/seed/`, then register it in `scripts/common.py::DOMAINS`.

`price_items_fts` mirrors description, category, and tags for SQLite FTS5 matching.
