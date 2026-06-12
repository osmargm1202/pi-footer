#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
from pathlib import Path

from common import DATA, DB_PATH, DOMAINS, connect, seed_rows

COLUMNS = "sku,category,description,unit,unit_price,currency,source,updated_at,tags"
PLACEHOLDERS = ",".join(["?"] * 9)


def build(db_path: Path = DB_PATH) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = connect(db_path)
    try:
        conn.executescript((DATA / "schema.sql").read_text(encoding="utf-8"))
        total = 0
        for domain in DOMAINS:
            for row in seed_rows(domain):
                values = [
                    row["sku"],
                    row["category"],
                    row["description"],
                    row["unit"],
                    float(row["unit_price"]),
                    row["currency"],
                    row["source"],
                    row["updated_at"],
                    row["tags"],
                ]
                conn.execute(f"INSERT INTO {domain} ({COLUMNS}) VALUES ({PLACEHOLDERS})", values)
                conn.execute(
                    f"INSERT INTO price_items (sku,domain,{COLUMNS.split(',', 1)[1]}) VALUES ({','.join(['?'] * 10)})",
                    [row["sku"], domain, *values[1:]],
                )
                total += 1
        conn.commit()
        return total
    except sqlite3.Error as exc:
        raise SystemExit(f"database build failed: {exc}") from exc
    finally:
        conn.close()


def main() -> int:
    total = build()
    print(f"built {DB_PATH} with {total} price items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
