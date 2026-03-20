-- Migration: Add ticker and quantity to custom_investments
-- Created: 2026-03-19
-- Description: Allows custom investments to represent stock positions with a ticker and quantity

ALTER TABLE custom_investments
  ADD COLUMN IF NOT EXISTS ticker   TEXT,
  ADD COLUMN IF NOT EXISTS quantity FLOAT;

COMMENT ON COLUMN custom_investments.ticker   IS 'Optional stock ticker symbol (e.g. AAPL). NULL for non-stock assets.';
COMMENT ON COLUMN custom_investments.quantity IS 'Number of shares held. NULL for non-stock assets where only amount matters.';

-- Rollback:
-- ALTER TABLE custom_investments DROP COLUMN IF EXISTS ticker;
-- ALTER TABLE custom_investments DROP COLUMN IF EXISTS quantity;
