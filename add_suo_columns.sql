-- =====================================================
-- Migration: Add Surplus Uplift Offset (SUO) columns
-- =====================================================
-- This migration adds columns to track SUO discount data
-- in the submissions table.
-- =====================================================

-- Add SUO columns to submissions table
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS suo_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS suo_discount_fraction FLOAT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS suo_eligible_surplus FLOAT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS suo_usable_surplus FLOAT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS suo_total_units FLOAT;

-- Add comments to document the columns
COMMENT ON COLUMN submissions.suo_enabled IS 'Whether Surplus Uplift Offset was applied to this submission';
COMMENT ON COLUMN submissions.suo_discount_fraction IS 'The discount percentage applied (e.g., 0.30 for 30%)';
COMMENT ON COLUMN submissions.suo_eligible_surplus IS 'Total Medium+ distinctiveness surplus units available';
COMMENT ON COLUMN submissions.suo_usable_surplus IS 'Usable surplus after applying 50% headroom';
COMMENT ON COLUMN submissions.suo_total_units IS 'Total units allocated in the submission';

-- Completion message
DO $$ 
BEGIN 
    RAISE NOTICE 'SUO columns added to submissions table successfully!';
END $$;
