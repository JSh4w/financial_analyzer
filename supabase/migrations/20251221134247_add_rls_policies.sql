-- Migration: Add Row Level Security (RLS) policies
-- Created: 2025-01-21
-- Description: Secure tables so users can only access their own data

-- Enable RLS on tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE bank_requisitions ENABLE ROW LEVEL SECURITY;

-- User Profiles Policies
CREATE POLICY "Users can view own profile"
  ON user_profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON user_profiles FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON user_profiles FOR INSERT
  WITH CHECK (auth.uid() = id);

-- Bank Requisitions Policies
CREATE POLICY "Users can view own requisitions"
  ON bank_requisitions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own requisitions"
  ON bank_requisitions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own requisitions"
  ON bank_requisitions FOR UPDATE
  USING (auth.uid() = user_id);

-- Rollback instructions:
-- DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
-- DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
-- DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;
-- DROP POLICY IF EXISTS "Users can view own requisitions" ON bank_requisitions;
-- DROP POLICY IF EXISTS "Users can insert own requisitions" ON bank_requisitions;
-- DROP POLICY IF EXISTS "Users can update own requisitions" ON bank_requisitions;
-- ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE bank_requisitions DISABLE ROW LEVEL SECURITY;
