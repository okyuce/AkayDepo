-- Fix revision_diff column type from INTEGER to TEXT
-- This allows storing JSON data for product differences in revision loadsheets

ALTER TABLE loadsheets 
ALTER COLUMN revision_diff TYPE TEXT USING revision_diff::text;

-- Verify the change
\d loadsheets;
