-- Point-in-time fundamentals for the Strategy V2 portfolio template basket.
-- Covers market_cap / ROE / revenue_growth / debt_to_equity used by templates 9 and 12.

INSERT INTO qd_fundamental_snapshots
  (market, symbol, period_end, available_at, frequency, currency,
   market_cap, return_on_equity, revenue_growth, debt_to_equity,
   source, source_version)
VALUES
  ('USStock', 'AAPL',  '2024-12-31', '2025-02-01', 'quarterly', 'USD', 3.00e12, 0.45, 0.08, 1.20, 'system_seed', '2025-02'),
  ('USStock', 'MSFT',  '2024-12-31', '2025-02-01', 'quarterly', 'USD', 3.10e12, 0.38, 0.12, 0.45, 'system_seed', '2025-02'),
  ('USStock', 'NVDA',  '2024-12-31', '2025-02-01', 'quarterly', 'USD', 2.20e12, 0.55, 0.35, 0.25, 'system_seed', '2025-02'),
  ('USStock', 'AMZN',  '2024-12-31', '2025-02-01', 'quarterly', 'USD', 1.90e12, 0.18, 0.11, 0.55, 'system_seed', '2025-02'),
  ('USStock', 'META',  '2024-12-31', '2025-02-01', 'quarterly', 'USD', 1.40e12, 0.32, 0.16, 0.30, 'system_seed', '2025-02'),
  ('USStock', 'GOOGL', '2024-12-31', '2025-02-01', 'quarterly', 'USD', 2.00e12, 0.28, 0.10, 0.15, 'system_seed', '2025-02'),
  ('USStock', 'AVGO',  '2024-12-31', '2025-02-01', 'quarterly', 'USD', 8.00e11, 0.25, 0.09, 0.90, 'system_seed', '2025-02'),
  ('USStock', 'COST',  '2024-12-31', '2025-02-01', 'quarterly', 'USD', 4.00e11, 0.22, 0.07, 0.40, 'system_seed', '2025-02'),
  ('USStock', 'JPM',   '2024-12-31', '2025-02-01', 'quarterly', 'USD', 6.00e11, 0.16, 0.05, 1.80, 'system_seed', '2025-02'),
  ('USStock', 'XOM',   '2024-12-31', '2025-02-01', 'quarterly', 'USD', 4.50e11, 0.14, 0.03, 0.35, 'system_seed', '2025-02')
ON CONFLICT (market, symbol, period_end, available_at, source) DO UPDATE SET
  market_cap = EXCLUDED.market_cap,
  return_on_equity = EXCLUDED.return_on_equity,
  revenue_growth = EXCLUDED.revenue_growth,
  debt_to_equity = EXCLUDED.debt_to_equity,
  frequency = EXCLUDED.frequency,
  currency = EXCLUDED.currency,
  source_version = EXCLUDED.source_version,
  ingested_at = NOW();
