from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DB_PATH = DATA / "presupuesto.db"
OUTPUT = ROOT / "output"
SEED = DATA / "seed"

DOMAINS = {
    "materials": "materials.csv",
    "labor": "labor.csv",
    "equipment": "equipment.csv",
    "earthworks": "earthworks.csv",
    "services": "services.csv",
    "cotizaciones": "cotizaciones_realizadas.csv",
}

COMPANIES = {
    "orgm": {
        "name": "ORGM",
        "logo_url": "https://r2.or-gm.com/orgm.png",
        "theme": "orgm.css",
    },
    "integra": {
        "name": "Integra",
        "logo_url": "",
        "theme": "integra.css",
    },
    "dapec": {
        "name": "DAPEC",
        "logo_url": "https://r2.or-gm.com/dapec.png",
        "theme": "dapec.css",
    },
}


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def seed_rows(domain: str) -> list[dict[str, str]]:
    with (SEED / DOMAINS[domain]).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def normalize_company(value: str | None) -> str:
    company = (value or "orgm").strip().lower()
    if company not in COMPANIES:
        raise SystemExit(f"unsupported company: {company}")
    return company
