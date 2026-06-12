PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS price_items_fts;
DROP TABLE IF EXISTS price_items;
DROP TABLE IF EXISTS materials;
DROP TABLE IF EXISTS labor;
DROP TABLE IF EXISTS equipment;
DROP TABLE IF EXISTS earthworks;
DROP TABLE IF EXISTS cotizaciones;
DROP TABLE IF EXISTS services;

CREATE TABLE materials (
  sku TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  description TEXT NOT NULL,
  unit TEXT NOT NULL,
  unit_price REAL NOT NULL CHECK (unit_price >= 0),
  currency TEXT NOT NULL DEFAULT 'USD',
  source TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT ''
);

CREATE TABLE labor AS SELECT * FROM materials WHERE 0;
CREATE TABLE equipment AS SELECT * FROM materials WHERE 0;
CREATE TABLE earthworks AS SELECT * FROM materials WHERE 0;
CREATE TABLE cotizaciones AS SELECT * FROM materials WHERE 0;
CREATE TABLE services AS SELECT * FROM materials WHERE 0;

CREATE TABLE price_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sku TEXT NOT NULL UNIQUE,
  domain TEXT NOT NULL,
  category TEXT NOT NULL,
  description TEXT NOT NULL,
  unit TEXT NOT NULL,
  unit_price REAL NOT NULL CHECK (unit_price >= 0),
  currency TEXT NOT NULL DEFAULT 'USD',
  source TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT ''
);

CREATE VIRTUAL TABLE price_items_fts USING fts5(
  sku UNINDEXED,
  domain,
  category,
  description,
  tags,
  content='price_items',
  content_rowid='id'
);

CREATE TRIGGER price_items_ai AFTER INSERT ON price_items BEGIN
  INSERT INTO price_items_fts(rowid, sku, domain, category, description, tags)
  VALUES (new.id, new.sku, new.domain, new.category, new.description, new.tags);
END;

CREATE TRIGGER price_items_ad AFTER DELETE ON price_items BEGIN
  INSERT INTO price_items_fts(price_items_fts, rowid, sku, domain, category, description, tags)
  VALUES ('delete', old.id, old.sku, old.domain, old.category, old.description, old.tags);
END;

CREATE TRIGGER price_items_au AFTER UPDATE ON price_items BEGIN
  INSERT INTO price_items_fts(price_items_fts, rowid, sku, domain, category, description, tags)
  VALUES ('delete', old.id, old.sku, old.domain, old.category, old.description, old.tags);
  INSERT INTO price_items_fts(rowid, sku, domain, category, description, tags)
  VALUES (new.id, new.sku, new.domain, new.category, new.description, new.tags);
END;
