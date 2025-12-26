-- Migration: Create bank_requisitions table
-- Created: 2025-01-22
-- Description: Stores GoCardless banking requisitions for users

-- Create bank_requisitions table
CREATE TABLE IF NOT EXISTS bank_requisitions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  requisition_id TEXT NOT NULL UNIQUE,
  institution_id TEXT NOT NULL,
  reference TEXT,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_bank_requisitions_user_id ON bank_requisitions(user_id);
CREATE INDEX IF NOT EXISTS idx_bank_requisitions_requisition_id ON bank_requisitions(requisition_id);
CREATE INDEX IF NOT EXISTS idx_bank_requisitions_status ON bank_requisitions(status);

-- Add updated_at trigger
DROP TRIGGER IF EXISTS update_bank_requisitions_updated_at ON bank_requisitions;
CREATE TRIGGER update_bank_requisitions_updated_at
  BEFORE UPDATE ON bank_requisitions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Add comment
COMMENT ON TABLE bank_requisitions IS 'GoCardless banking requisitions linked to users';

-- Rollback instructions:
-- DROP TRIGGER IF EXISTS update_bank_requisitions_updated_at ON bank_requisitions;
-- DROP TABLE IF EXISTS bank_requisitions CASCADE;
