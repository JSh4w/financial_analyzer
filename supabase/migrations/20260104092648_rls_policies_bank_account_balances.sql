-- Migration: Add Row Level Security (RLS) policies
-- Created: 2025-01-04
-- Description: Secure tables so users can only access their own data

-- Enable RLS on tables
ALTER TABLE bank_account_balances ENABLE ROW LEVEL SECURITY;

-- User Profiles Policies
CREATE POLICY "Users can view own profile"
  ON bank_account_balances FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON bank_account_balances FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON bank_account_balances FOR INSERT
  WITH CHECK (auth.uid() = id);

-- Rollback instructions:
-- DROP POLICY IF EXISTS "Users can view own profile" ON bank_account_balances;
-- DROP POLICY IF EXISTS "Users can update own profile" ON bank_account_balances;
-- DROP POLICY IF EXISTS "Users can insert own profile" ON bank_account_balances;
-- ALTER TABLE bank_account_balances DISABLE ROW LEVEL SECURITY;
