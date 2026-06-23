-- Add display_name field to vm_definitions for reusable config/template naming

-- Add display_name column (nullable initially for safe migration)
ALTER TABLE vm_definitions ADD COLUMN display_name VARCHAR(255);

-- Backfill display_name from vm_name for existing records
UPDATE vm_definitions SET display_name = vm_name WHERE display_name IS NULL;

-- Make display_name NOT NULL after backfill
ALTER TABLE vm_definitions ALTER COLUMN display_name SET NOT NULL;

-- Add uniqueness constraint for display_name
ALTER TABLE vm_definitions ADD CONSTRAINT vm_definitions_display_name_unique UNIQUE (display_name);

-- Add index for efficient lookups
CREATE INDEX idx_vm_definitions_display_name ON vm_definitions(display_name);

-- Comments for documentation
COMMENT ON COLUMN vm_definitions.display_name IS 'Human-readable config/template name (must be unique)';
