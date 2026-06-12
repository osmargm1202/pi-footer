#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from common import DOMAINS, SEED

REQUIRED = ["sku", "category", "description", "unit", "unit_price", "currency", "source", "updated_at", "tags"]


def import_csv_rows(source: Path, target: Path, append: bool = True) -> int:
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in REQUIRED if name not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"missing required columns: {', '.join(missing)}")
        rows = [{name: (row.get(name) or "").strip() for name in REQUIRED} for row in reader]

    target.parent.mkdir(parents=True, exist_ok=True)
    file_exists = target.exists() and target.stat().st_size > 0
    mode = "a" if append and file_exists else "w"
    with target.open(mode, newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED)
        if mode == "w":
            writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import normalized catalog CSV rows into a seed CSV file")
    parser.add_argument("source", type=Path, help="CSV with sku,category,description,unit,unit_price,currency,source,updated_at,tags")
    parser.add_argument("domain", choices=sorted(DOMAINS), help="target seed domain")
    parser.add_argument("--replace", action="store_true", help="replace target seed file instead of appending")
    args = parser.parse_args()
    target = SEED / DOMAINS[args.domain]
    count = import_csv_rows(args.source, target, append=not args.replace)
    action = "replaced" if args.replace else "imported"
    print(f"{action} {count} rows into {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
