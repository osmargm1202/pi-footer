#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3

from common import DB_PATH, connect


def ensure_db() -> None:
    if not DB_PATH.exists():
        from build_db import build

        build(DB_PATH)


def search(query: str, limit: int = 5) -> list[dict[str, object]]:
    ensure_db()
    fts_query = " OR ".join(part.strip() for part in query.split() if part.strip()) or query
    conn = connect(DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT p.sku, p.domain, p.category, p.description, p.unit,
                   p.unit_price, p.currency, p.source, p.updated_at, p.tags,
                   bm25(price_items_fts) AS score
            FROM price_items_fts
            JOIN price_items p ON p.id = price_items_fts.rowid
            WHERE price_items_fts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = conn.execute(
            """
            SELECT sku, domain, category, description, unit, unit_price,
                   currency, source, updated_at, tags, 0 AS score
            FROM price_items
            WHERE lower(description || ' ' || category || ' ' || tags) LIKE lower(?)
            LIMIT ?
            """,
            (f"%{query}%", limit),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description="Search presupuesto price items")
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(search(args.query, args.limit), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
