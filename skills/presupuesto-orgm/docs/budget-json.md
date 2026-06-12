# Budget JSON

`output/presupuesto.json` is self-contained and mirrors current ConstruCosto structure.

## Top-level structure

- `company`: theme selector, one of `orgm`, `integra`, `dapec`; defaults to `orgm`.
- `project`: `name`, `voltage`, `client`, `documentTitle`, `revision`, `date`, `location`.
- `currency`: object with `base`, `symbol`, optional `usdRate`, `showUsdConversion`, `rateSource`, `rateKey`.
- `taxes`: `{ "itbisPercent": 18 }`.
- `metadata`: provenance/status notes; may include `company` override for rendering.
- `partidas[]`: budget sections.
- `indirectos[]`: percent or fixed indirect cost lines.
- `consideraciones`: `{ "generales": [...] }`.
- `totals`: calculated by generator/renderer for subtotal partidas, indirectos, ITBIS, total general.

## Partidas

```json
{
  "code": "1",
  "title": "Cimentación",
  "description": "Zapatas, excavaciones y hormigón.",
  "subcategories": [
    {
      "code": "1.1",
      "title": "Hormigón",
      "items": [
        {"code": "1.1.1", "description": "Hormigón 210 kg/cm2", "unit": "m3", "quantity": 18, "unitPrice": 9255.5, "sourceId": "materiales-0088", "basis": "Catálogo ConstruCosto"}
      ]
    }
  ],
  "consideraciones": ["Validar cantidades contra planos IFC."]
}
```

## Request shortcuts

`generate_presupuesto.py` accepts either full `partidas[]` or simpler `items[]`. Simple items are grouped by `partida` and `subcategory`, matched through SQLite FTS, then written as full `partidas[].subcategories[].items[]`.

See `docs/sample-request.json`.
