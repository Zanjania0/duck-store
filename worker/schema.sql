CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  user_name TEXT,
  order_type TEXT NOT NULL DEFAULT 'rent_gift',
  items_json TEXT,
  items_text TEXT,
  total_price REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending_receipt',
  fragment_link TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
INSERT OR IGNORE INTO settings(key,value) VALUES('config','{}');
