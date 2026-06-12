# Themes

`render_html.py` picks company in this order:

1. `--company orgm|integra|dapec`
2. top-level `company`
3. `metadata.company`
4. `project.client` if it matches a known company
5. default `orgm`

It copies matching CSS to `output/theme.css` and renders A4 print pages with repeated header/footer.

## ORGM

Default theme. Purple/sky accent. Uses `https://r2.or-gm.com/orgm.png` when local `assets/orgm.png` is missing.

## Integra

Current ConstruCosto blue/gold palette adapted from source `css/print.css`.

## DAPEC

Green/blue technical theme. Uses `https://r2.or-gm.com/dapec.png` when local `assets/dapec.png` is missing.

Logo download is best-effort. If download fails, rendered HTML keeps remote logo URL so print preview still has a usable reference when online.
