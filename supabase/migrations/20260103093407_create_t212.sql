-- Migration: Create t212 table
-- Created: 2026-01-03 09:34:07
-- Description: Stores T212 keys for users
-- Create t212 table
CREATE TABLE IF NOT EXISTS t212 (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  t212_key_id TEXT NOT NULL,
  t212_key_secret TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_t212_user_id ON t212(user_id);
CREATE INDEX IF NOT EXISTS idx_t212_key_id ON t212(t212_key_id);

-- Add updated_at trigger
DROP TRIGGER IF EXISTS update_t212_updated_at ON t212;
CREATE TRIGGER update_t212_updated_at
  BEFORE UPDATE ON t212
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Add comment
COMMENT ON TABLE t212 IS 'T212 keys linked to users';

-- Rollback instructions:
-- DROP TRIGGER IF EXISTS update_t212_updated_at ON t212;
-- DROP TABLE IF EXISTS t212 CASCADE;