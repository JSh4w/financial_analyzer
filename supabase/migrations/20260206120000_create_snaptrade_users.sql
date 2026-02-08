-- Migration: Create snaptrade_users table
-- Created: 2026-02-06
-- Description: Stores SnapTrade user secrets (encrypted) for brokerage integration

-- Create snaptrade_users table
CREATE TABLE IF NOT EXISTS snaptrade_users (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  user_secret TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add index for fast lookups by user_id
CREATE INDEX IF NOT EXISTS idx_snaptrade_users_user_id ON snaptrade_users(user_id);

-- Add updated_at trigger
DROP TRIGGER IF EXISTS update_snaptrade_users_updated_at ON snaptrade_users;
CREATE TRIGGER update_snaptrade_users_updated_at
  BEFORE UPDATE ON snaptrade_users
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Add comment
COMMENT ON TABLE snaptrade_users IS 'SnapTrade user secrets for brokerage account connections (encrypted at application level)';

-- Rollback instructions:
-- DROP TRIGGER IF EXISTS update_snaptrade_users_updated_at ON snaptrade_users;
-- DROP TABLE IF EXISTS snaptrade_users CASCADE;
