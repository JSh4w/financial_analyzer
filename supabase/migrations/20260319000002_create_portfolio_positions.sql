-- Migration: Create portfolio_positions table
-- Created: 2026-03-19
-- Description: Stores synced stock/fund positions from T212, SnapTrade, and other brokerages.
--              Used for batch processing (Monte Carlo), cross-user aggregation, and net worth history.

CREATE TABLE IF NOT EXISTS portfolio_positions (
  id           UUID                     DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id      UUID                     NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  source            TEXT                     NOT NULL,  -- 't212', 'snaptrade', 'custom'
  ticker            TEXT                     NOT NULL,
  quantity          FLOAT,                             -- Fernet-encrypted, private
  avg_price         TEXT,                              -- Fernet-encrypted float (cost basis), private
  portfolio_fraction FLOAT,                            -- Fraction of total portfolio value (0.0–1.0), shareable
  last_synced  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portfolio_positions_user_id ON portfolio_positions(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_positions_ticker  ON portfolio_positions(ticker);

COMMENT ON TABLE  portfolio_positions              IS 'Synced brokerage stock positions. Source indicates origin (t212, snaptrade, custom).';
COMMENT ON COLUMN portfolio_positions.quantity          IS 'Number of shares held. Private — never exposed cross-user.';
COMMENT ON COLUMN portfolio_positions.avg_price         IS 'Fernet-encrypted cost basis per share. Private — never exposed cross-user.';
COMMENT ON COLUMN portfolio_positions.portfolio_fraction IS 'Fraction of total portfolio value (0.0–1.0). Safe to aggregate/share across users.';
COMMENT ON COLUMN portfolio_positions.last_synced  IS 'Timestamp of last sync from the source brokerage.';

-- Rollback:
-- DROP TABLE IF EXISTS portfolio_positions CASCADE;
