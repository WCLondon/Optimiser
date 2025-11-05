-- Add password column to introducers table
-- This allows each promoter to have their own password for login

-- Add password column (if it doesn't exist)
ALTER TABLE introducers 
ADD COLUMN IF NOT EXISTS password TEXT;

-- Set default passwords for existing introducers (optional - update as needed)
-- You can update these to actual passwords after running this migration

-- Example: Set password to name + '1' for existing records without password
UPDATE introducers 
SET password = name || '1' 
WHERE password IS NULL OR password = '';

-- Or set specific passwords for each introducer:
-- UPDATE introducers SET password = 'secure_password_here' WHERE name = 'ETP';
-- UPDATE introducers SET password = 'secure_password_here' WHERE name = 'Arbtech';
-- UPDATE introducers SET password = 'secure_password_here' WHERE name = 'Cypher';
