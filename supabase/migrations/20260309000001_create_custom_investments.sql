-- Migration: Create custom_investments table
-- Created: 2026-03-09
-- Description: Stores user-defined investment amounts (amount encrypted at application level)

CREATE TABLE IF NOT EXISTS custom_investments (
  id          UUID                     DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID                     NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name        TEXT                     NOT NULL,
  description TEXT,
  amount      TEXT                     NOT NULL, -- Fernet-encrypted float value
  created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_custom_investments_user_id ON custom_investments(user_id);

DROP TRIGGER IF EXISTS update_custom_investments_updated_at ON custom_investments;
CREATE TRIGGER update_custom_investments_updated_at
  BEFORE UPDATE ON custom_investments
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE custom_investments IS 'User-defined investment amounts (amount encrypted at application level via Fernet)';

-- Rollback:
-- DROP TRIGGER IF EXISTS update_custom_investments_updated_at ON custom_investments;
-- DROP TABLE IF EXISTS custom_investments CASCADE;
