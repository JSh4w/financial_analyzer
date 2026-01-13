-- Migration: Create end_agreements table
-- Created: 2026-01-13
-- Description: Stores end agreements for banks, used in making requisitions

-- Create end_agreements table
CREATE TABLE IF NOT EXISTS end_agreements (
  agreement_id TEXT PRIMARY KEY,
  institution_id TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add comment
COMMENT ON TABLE end_agreements IS 'GoCardless end agreement asking for 7 days access to a specific bank type';

-- Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_end_agreements_updated_at
  BEFORE UPDATE ON end_agreements
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Rollback instructions:
-- DROP TRIGGER IF EXISTS update_end_agreements_updated_at ON end_agreements;
-- DROP FUNCTION IF EXISTS update_updated_at_column();
-- DROP TABLE IF EXISTS end_agreements CASCADE;
