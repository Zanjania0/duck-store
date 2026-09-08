CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO settings(key,value) VALUES ('rent_settings','{}');
INSERT OR IGNORE INTO settings(key,value) VALUES ('rent_cache','{"gifts":[]}');
INSERT OR IGNORE INTO settings(key,value) VALUES ('last_rate','0');
