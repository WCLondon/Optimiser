-- =====================================================
-- Gross Inventory Schema for BNG Optimiser
-- =====================================================
-- This schema supports the new gross-based optimization algorithm
-- where we track both gross units (total habitat created) and
-- baseline units (habitat lost during creation).
--
-- The key insight is that when a habitat bank creates new habitat,
-- it destroys some existing baseline habitat. The NET yield is:
-- NET = GROSS - BASELINE
--
-- By using GROSS units and tracking baselines separately, we can:
-- 1. Offset baseline losses with customer's on-site surplus
-- 2. Use cheaper habitats to cover baseline shortfalls
-- 3. Only fall back to NET when baseline = new habitat (avoid loops)
-- =====================================================

-- Table: GrossInventory
-- Tracks the detailed inventory of each habitat parcel at each bank
-- This replaces/supplements the Stock table for gross-based optimization
CREATE TABLE IF NOT EXISTS "GrossInventory" (
    id SERIAL PRIMARY KEY,
    
    -- Unique identifier for this inventory row
    unique_id TEXT NOT NULL UNIQUE,
    
    -- Bank identification
    bank_id TEXT NOT NULL,
    bank_name TEXT NOT NULL,
    bank_postcode TEXT,  -- Postcode for geocoding and tier calculations
    bgs_reference TEXT,  -- Biodiversity Gain Site Reference (e.g., BGS-150825001)
    habitat_reference TEXT,  -- Habitat Reference (e.g., HAB-00004166-BM4S1)
    
    -- Ledger type (CRITICAL: no inter-ledger trading allowed!)
    ledger_type TEXT NOT NULL DEFAULT 'area',  -- 'area', 'hedgerow', or 'watercourse'
    
    -- Baseline (original) habitat information
    baseline_habitat TEXT,  -- The habitat that was on site before (e.g., "Cereal crops")
    baseline_area FLOAT DEFAULT 0,  -- Area/Length of baseline habitat
    baseline_units FLOAT DEFAULT 0,  -- Units of baseline habitat lost
    
    -- New (created) habitat information
    new_habitat TEXT NOT NULL,  -- The habitat being created (e.g., "Traditional orchards")
    new_area FLOAT DEFAULT 0,  -- Area/Length of new habitat
    gross_units FLOAT NOT NULL DEFAULT 0,  -- Total units of new habitat created
    net_units FLOAT NOT NULL DEFAULT 0,  -- Useable units = gross - baseline
    
    -- Yield per unit area (for reference/calculations)
    gross_yield_per_area FLOAT,  -- Gross yield per unit area
    net_yield_per_area FLOAT,  -- Net yield per unit area
    
    -- Allocation tracking
    reserved_units FLOAT DEFAULT 0,  -- Units reserved but not yet allocated
    allocated_units FLOAT DEFAULT 0,  -- Units already allocated to customers
    allocated_area FLOAT DEFAULT 0,  -- Area already allocated
    remaining_units FLOAT DEFAULT 0,  -- Units available for sale
    remaining_area FLOAT DEFAULT 0,  -- Area available
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Foreign key to Banks table
    FOREIGN KEY (bank_id) REFERENCES "Banks"(bank_id) ON DELETE CASCADE
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_gross_inventory_bank ON "GrossInventory"(bank_id);
CREATE INDEX IF NOT EXISTS idx_gross_inventory_new_habitat ON "GrossInventory"(new_habitat);
CREATE INDEX IF NOT EXISTS idx_gross_inventory_postcode ON "GrossInventory"(bank_postcode);
CREATE INDEX IF NOT EXISTS idx_gross_inventory_baseline_habitat ON "GrossInventory"(baseline_habitat);
CREATE INDEX IF NOT EXISTS idx_gross_inventory_unique_id ON "GrossInventory"(unique_id);
CREATE INDEX IF NOT EXISTS idx_gross_inventory_remaining ON "GrossInventory"(remaining_units);

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_gross_inventory_updated_at BEFORE UPDATE ON "GrossInventory"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View: Available gross inventory with calculated fields
CREATE OR REPLACE VIEW "GrossInventoryAvailable" AS
SELECT 
    gi.unique_id,
    gi.bank_id,
    gi.bank_name,
    gi.bank_postcode,
    gi.ledger_type,  -- CRITICAL: needed for inter-ledger trading check
    gi.baseline_habitat,
    gi.baseline_units,
    gi.new_habitat,
    gi.gross_units,
    gi.net_units,
    gi.remaining_units,
    -- Calculate if this is a "same habitat" situation (baseline = new)
    CASE 
        WHEN gi.baseline_habitat = gi.new_habitat THEN TRUE
        WHEN gi.baseline_habitat IS NULL OR gi.baseline_habitat = '' THEN FALSE
        ELSE FALSE
    END AS same_habitat_baseline,
    -- Calculate baseline units per gross unit (for proportional allocation)
    CASE 
        WHEN gi.gross_units > 0 THEN gi.baseline_units / gi.gross_units
        ELSE 0
    END AS baseline_ratio,
    b.lpa_name,
    b.nca_name
FROM "GrossInventory" gi
LEFT JOIN "Banks" b ON gi.bank_id = b.bank_id
WHERE gi.remaining_units > 0;

-- =====================================================
-- Sample Data Insert (matching the provided example)
-- =====================================================
-- Run this INSERT statement to populate the GrossInventory table with sample data

INSERT INTO "GrossInventory" (
    unique_id, bank_id, bank_name, bank_postcode, bgs_reference, habitat_reference,
    ledger_type,  -- 'area', 'hedgerow', or 'watercourse'
    baseline_habitat, baseline_area, baseline_units,
    new_habitat, new_area, gross_units, net_units,
    gross_yield_per_area, net_yield_per_area,
    reserved_units, allocated_units, allocated_area,
    remaining_units, remaining_area
) VALUES 
-- Area habitats
(
    'Wild HordenBGS-150825001HAB-00004166-BM4S1',
    'wild_horden', 'Wild Horden', 'TS21 1AA', 'BGS-150825001', 'HAB-00004166-BM4S1',
    'area',
    'Cereal crops', 2.80494, 5.60988,
    'Traditional orchards', 2.80494, 16.50635148, 10.89647148,
    5.884743162, 3.884743162,
    0, 0, 0,
    10.89647148, 2.80494
),
(
    'Wild HordenBGS-150825001HAB-00004164-BG0N0',
    'wild_horden', 'Wild Horden', 'TS21 1AA', 'BGS-150825001', 'HAB-00004164-BG0N0',
    'area',
    'Cereal crops', 2.780805, 5.56161,
    'Mixed scrub', 2.780805, 23.36818139, 17.80657139,
    8.40338729, 6.40338729,
    0, 0, 0,
    17.80657139, 2.780805
),
(
    'Wild HordenBGS-150825001HAB-00004162-BQ3D5',
    'wild_horden', 'Wild Horden', 'TS21 1AA', 'BGS-150825001', 'HAB-00004162-BQ3D5',
    'area',
    'Modified grassland', 0.72, 2.88,
    'Lowland calcareous grassland', 0.72, 4.022336023, 1.142336023,
    5.58657781, 1.58657781,
    0, 0.351532921, 0.22156677,
    0.790803103, 0.49843323
),
(
    'Wild HordenBGS-150825001HAB-00004160-BD5Y3',
    'wild_horden', 'Wild Horden', 'TS21 1AA', 'BGS-150825001', 'HAB-00004160-BD5Y3',
    'area',
    'Cereal crops', 2.780805, 5.56161,
    'Other neutral grassland', 2.780805, 23.27, 17.70839,
    8.368080466, 6.368080466,
    0, 0, 0,
    17.70839, 2.780805
),
-- Hedgerow habitats
(
    'Wild HordenBGS-150825001HAB-00004165-BN3D0',
    'wild_horden', 'Wild Horden', 'TS21 1AA', 'BGS-150825001', 'HAB-00004165-BN3D0',
    'hedgerow',
    'Native hedgerow', 0.2, 0.8,
    'Species-rich native hedgerow with trees', 0.2, 2.760790368, 1.960790368,
    13.80395184, 9.803951839,
    0, 0, 0,
    1.960790368, 0.2
),
(
    'Wild HordenBGS-150825001HAB-00004161-BS4X2',
    'wild_horden', 'Wild Horden', 'TS21 1AA', 'BGS-150825001', 'HAB-00004161-BS4X2',
    'hedgerow',
    'Native hedgerow', 0.166, 0.332,
    'Species-rich native hedgerow with trees', 0.166, 2.19194972, 1.85994972,
    13.20451639, 11.20451639,
    0, 0, 0,
    1.85994972, 0.166
),
(
    'Wild HordenBGS-150825001HAB-00004163-BW6X7',
    'wild_horden', 'Wild Horden', 'TS21 1AA', 'BGS-150825001', 'HAB-00004163-BW6X7',
    'hedgerow',
    NULL, 0.2984, 0,  -- No baseline habitat
    'Species-rich native hedgerow with trees', 0.2984, 2.634011039, 2.634011039,
    8.827114743, 8.827114743,
    0, 0, 0,
    2.634011039, 0.2984
)
ON CONFLICT (unique_id) DO NOTHING;

-- =====================================================
-- Completion message
-- =====================================================
DO $$ 
BEGIN 
    RAISE NOTICE 'GrossInventory schema created successfully!';
END $$;
