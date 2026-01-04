-- Migration: Add Row Level Security (RLS) policies
-- Created: 2025-01-04
-- Description: Secure tables so users can only access their own data

-- Enable RLS on tables
ALTER TABLE t212 ENABLE ROW LEVEL SECURITY;

-- User Profiles Policies
CREATE POLICY "Users can view own profile"
  ON t212 FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON t212 FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON t212 FOR INSERT
  WITH CHECK (auth.uid() = id);

-- Rollback instructions:
-- DROP POLICY IF EXISTS "Users can view own profile" ON t212;
-- DROP POLICY IF EXISTS "Users can update own profile" ON t212;
-- DROP POLICY IF EXISTS "Users can insert own profile" ON t212;
-- ALTER TABLE t212 DISABLE ROW LEVEL SECURITY;
