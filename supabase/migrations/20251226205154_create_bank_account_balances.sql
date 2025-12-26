-- Migration: Create bank_account_balances table
-- Created: 2025-12-26
-- Description: Stores bank account balance information with rate limit tracking

-- Create bank_account_balances table
CREATE TABLE IF NOT EXISTS bank_account_balances (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  account_id TEXT NOT NULL UNIQUE,
  balances JSONB NOT NULL,
  last_fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  can_refresh_at TIMESTAMP WITH TIME ZONE,
  rate_limit_remaining INTEGER,
  rate_limit_reset_seconds INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_bank_account_balances_user_id ON bank_account_balances(user_id);
CREATE INDEX IF NOT EXISTS idx_bank_account_balances_account_id ON bank_account_balances(account_id);
CREATE INDEX IF NOT EXISTS idx_bank_account_balances_can_refresh_at ON bank_account_balances(can_refresh_at);

-- Add updated_at trigger
DROP TRIGGER IF EXISTS update_bank_account_balances_updated_at ON bank_account_balances;
CREATE TRIGGER update_bank_account_balances_updated_at
  BEFORE UPDATE ON bank_account_balances
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Add comment
COMMENT ON TABLE bank_account_balances IS 'Bank account balance data with rate limit tracking for GoCardless API';
COMMENT ON COLUMN bank_account_balances.balances IS 'JSONB array of balance objects from GoCardless API';
COMMENT ON COLUMN bank_account_balances.can_refresh_at IS 'Timestamp when the balance data can be refreshed based on rate limits';
COMMENT ON COLUMN bank_account_balances.rate_limit_remaining IS 'Number of remaining API calls in the current rate limit window';
COMMENT ON COLUMN bank_account_balances.rate_limit_reset_seconds IS 'Seconds until rate limit resets (stored for reference)';

-- Rollback instructions:
-- DROP TRIGGER IF EXISTS update_bank_account_balances_updated_at ON bank_account_balances;
-- DROP TABLE IF EXISTS bank_account_balances CASCADE;
