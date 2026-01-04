-- Migration: enforce_unique_user_t212
-- Created: 2026-01-04
-- Description: Enforce one T212 key per user and remove redundant index

-- 1. Add UNIQUE constraint on user_id (only if it doesn't already exist)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 't212_user_unique'
  ) THEN
    ALTER TABLE t212
    ADD CONSTRAINT t212_user_unique UNIQUE (user_id);
  END IF;
END $$;

-- 2. Drop redundant index (UNIQUE constraint already creates one)
DROP INDEX IF EXISTS idx_t212_user_id;
