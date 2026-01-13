-- Migration: Create end_agreements table
-- Created: 2026-1-13
-- Description: Stores end agreements for banks, used in making requisitions

-- Create end_agreements table
CREATE TABLE IF NOT EXISTS end_agreements (
  agreement_id TEXT NOT NULL UNIQUE,
  institution_id TEXT NOT NULL,
);

-- Add comment
COMMENT ON TABLE end_agreements IS 'GoCardless end agreement asking for 7 days access to a specific bank type';

-- Rollback instructions:
-- DROP TRIGGER IF EXISTS update_end_agreements_updated_at ON end_agreements;
-- DROP TABLE IF EXISTS end_agreements CASCADE;
