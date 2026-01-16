-- Migration: Create user_subscriptions table
-- Purpose: Store persistent stock symbol subscriptions for each user
-- Created: 2025-01-15

-- Create user_subscriptions table
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    subscribed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,

    -- Ensure each user can only have one subscription per symbol
    CONSTRAINT unique_user_symbol UNIQUE(user_id, symbol)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id
    ON user_subscriptions(user_id);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_symbol
    ON user_subscriptions(symbol);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_active_symbol
    ON user_subscriptions(is_active, symbol);

-- Add Row Level Security (RLS) for Supabase
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own subscriptions
CREATE POLICY "Users can view their own subscriptions"
    ON user_subscriptions
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can insert their own subscriptions
CREATE POLICY "Users can create their own subscriptions"
    ON user_subscriptions
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own subscriptions
CREATE POLICY "Users can update their own subscriptions"
    ON user_subscriptions
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Policy: Users can delete their own subscriptions
CREATE POLICY "Users can delete their own subscriptions"
    ON user_subscriptions
    FOR DELETE
    USING (auth.uid() = user_id);

-- Comment for documentation
COMMENT ON TABLE user_subscriptions IS 'Stores persistent stock symbol subscriptions for users';
COMMENT ON COLUMN user_subscriptions.user_id IS 'Reference to auth.users table';
COMMENT ON COLUMN user_subscriptions.symbol IS 'Stock symbol (e.g., AAPL, TSLA)';
COMMENT ON COLUMN user_subscriptions.is_active IS 'Whether subscription is currently active (soft delete)';
COMMENT ON COLUMN user_subscriptions.last_active_at IS 'Last time user accessed this subscription (for cleanup)';
