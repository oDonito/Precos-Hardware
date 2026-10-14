CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  target REAL NOT NULL,
  shipping_cep TEXT NOT NULL DEFAULT '71592074'
);

CREATE TABLE IF NOT EXISTS observations (
  id TEXT PRIMARY KEY,
  item_id TEXT NOT NULL,
  item_name TEXT NOT NULL,
  store TEXT NOT NULL,
  price REAL,
  shipping REAL,
  total REAL,
  collected_at TEXT NOT NULL,
  url TEXT,
  seller TEXT,
  availability TEXT,
  confidence TEXT,
  notes TEXT
);

CREATE INDEX IF NOT EXISTS observations_collected_at_idx ON observations(collected_at DESC);
CREATE INDEX IF NOT EXISTS observations_item_store_idx ON observations(item_id, store, collected_at DESC);

INSERT OR IGNORE INTO items (id, name, category, target) VALUES
('monitor-lg-34g600a', 'Monitor Gamer LG UltraGear Curvo 34G600A-B 34" QuadHD 2K UltraWide 1800R, 160Hz', 'Monitor', 1450.00),
('suporte-monitor-35', 'Suporte de mesa articulado para até 35"', 'Suporte de monitor', 190.00),
('ryzen-5-7600x', 'Ryzen 5 7600X, 6-Core, 12-Threads, 4.7GHz (5.3GHz Turbo)', 'Processador (CPU)', 1000.00),
('radeon-rx-9070xt', 'AMD Radeon RX 9070 XT 16GB VRAM', 'Placa de Vídeo (GPU)', 4500.00),
('gigabyte-b650m-gaming-wifi', 'Placa-Mãe Gigabyte B650M Gaming WIFI, B650, AMD AM5, M-ATX, DDR5', 'Placa-Mãe (Motherboard)', 609.99),
('memoria-ddr5-16gb-5600', 'Memória RAM 16GB DDR5 5600MHz', 'Memória RAM', 1200.00),
('ssd-nvme-1tb-6000', 'SSD 1TB NVMe M.2, leitura 6000 MB/s', 'Armazenamento (SSD)', 800.00),
('fonte-850w-bronze', 'Fonte 850W 80 Plus Bronze MSI MAG / Corsair', 'Fonte de Alimentação (PSU)', 325.00),
('aircooler-ak400-ag400', 'Air Cooler DeepCool AK400 / AG400', 'Cooler do Processador', 190.00),
('gabinete-mid-tower-mesh', 'Gabinete Gamer Mid Tower, frente Mesh, 3x Fans ARGB', 'Gabinete Gamer', 140.00);
