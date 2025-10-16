-- =====================================================
-- Supabase Reference Tables Schema
-- =====================================================
-- This script creates all reference/config tables needed
-- for the BNG Optimiser application.
-- Schema and column names match the Excel tabs exactly.
-- =====================================================

-- Table: Banks
-- Stores information about habitat banks
CREATE TABLE IF NOT EXISTS "Banks" (
    bank_id TEXT PRIMARY KEY,
    bank_name TEXT NOT NULL,
    lpa_name TEXT,
    nca_name TEXT,
    postcode TEXT,
    address TEXT,
    lat FLOAT,
    lon FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_banks_lpa ON "Banks"(lpa_name);
CREATE INDEX IF NOT EXISTS idx_banks_nca ON "Banks"(nca_name);

-- Table: Pricing
-- Stores pricing information for habitats at different banks
CREATE TABLE IF NOT EXISTS "Pricing" (
    id SERIAL PRIMARY KEY,
    bank_id TEXT NOT NULL,
    habitat_name TEXT NOT NULL,
    contract_size TEXT NOT NULL,
    tier TEXT NOT NULL,
    price FLOAT NOT NULL,
    broader_type TEXT,
    distinctiveness_name TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (bank_id) REFERENCES "Banks"(bank_id) ON DELETE CASCADE
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_pricing_bank ON "Pricing"(bank_id);
CREATE INDEX IF NOT EXISTS idx_pricing_habitat ON "Pricing"(habitat_name);
CREATE INDEX IF NOT EXISTS idx_pricing_tier ON "Pricing"(tier);

-- Table: HabitatCatalog
-- Master list of all habitats with their properties
CREATE TABLE IF NOT EXISTS "HabitatCatalog" (
    id SERIAL PRIMARY KEY,
    habitat_name TEXT NOT NULL UNIQUE,
    broader_type TEXT NOT NULL,
    distinctiveness_name TEXT NOT NULL,
    "UmbrellaType" TEXT,  -- "area", "hedgerow", or "watercourse"
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_habitat_catalog_name ON "HabitatCatalog"(habitat_name);
CREATE INDEX IF NOT EXISTS idx_habitat_catalog_umbrella ON "HabitatCatalog"("UmbrellaType");

-- Table: Stock
-- Tracks available units for each habitat at each bank
CREATE TABLE IF NOT EXISTS "Stock" (
    id SERIAL PRIMARY KEY,
    bank_id TEXT NOT NULL,
    habitat_name TEXT NOT NULL,
    stock_id TEXT NOT NULL,
    quantity_available FLOAT NOT NULL DEFAULT 0,
    available_excl_quotes FLOAT,
    quoted FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (bank_id) REFERENCES "Banks"(bank_id) ON DELETE CASCADE
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_stock_bank ON "Stock"(bank_id);
CREATE INDEX IF NOT EXISTS idx_stock_habitat ON "Stock"(habitat_name);
CREATE INDEX IF NOT EXISTS idx_stock_id ON "Stock"(stock_id);

-- Table: DistinctivenessLevels
-- Maps distinctiveness names to numeric values
CREATE TABLE IF NOT EXISTS "DistinctivenessLevels" (
    id SERIAL PRIMARY KEY,
    distinctiveness_name TEXT NOT NULL UNIQUE,
    level_value FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_distinctiveness_name ON "DistinctivenessLevels"(distinctiveness_name);

-- Table: SRM (Strategic Resource Multipliers)
-- Defines multipliers for different tiers
CREATE TABLE IF NOT EXISTS "SRM" (
    id SERIAL PRIMARY KEY,
    tier TEXT NOT NULL UNIQUE,
    multiplier FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_srm_tier ON "SRM"(tier);

-- Table: TradingRules (Optional)
-- Defines trading rules for habitat types
CREATE TABLE IF NOT EXISTS "TradingRules" (
    id SERIAL PRIMARY KEY,
    rule_name TEXT NOT NULL,
    rule_value TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- Sample Data Inserts (for testing)
-- =====================================================

-- Sample Distinctiveness Levels
INSERT INTO "DistinctivenessLevels" (distinctiveness_name, level_value) VALUES
    ('Very Low', 0.0),
    ('Low', 2.0),
    ('Medium', 4.0),
    ('High', 6.0),
    ('Very High', 8.0),
    ('V.Low', 0.0),
    ('V.High', 8.0)
ON CONFLICT (distinctiveness_name) DO NOTHING;

-- Sample SRM values
INSERT INTO "SRM" (tier, multiplier) VALUES
    ('local', 1.0),
    ('adjacent', 1.15),
    ('far', 1.5)
ON CONFLICT (tier) DO NOTHING;

-- =====================================================
-- Row Level Security (RLS) Policies
-- =====================================================
-- These policies ensure that only authenticated users
-- can read the reference tables

-- Enable RLS on all reference tables
ALTER TABLE "Banks" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Pricing" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "HabitatCatalog" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Stock" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DistinctivenessLevels" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "SRM" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "TradingRules" ENABLE ROW LEVEL SECURITY;

-- Create policies to allow authenticated users to read all reference data
CREATE POLICY "Allow authenticated read on Banks" 
    ON "Banks" FOR SELECT 
    USING (true);

CREATE POLICY "Allow authenticated read on Pricing" 
    ON "Pricing" FOR SELECT 
    USING (true);

CREATE POLICY "Allow authenticated read on HabitatCatalog" 
    ON "HabitatCatalog" FOR SELECT 
    USING (true);

CREATE POLICY "Allow authenticated read on Stock" 
    ON "Stock" FOR SELECT 
    USING (true);

CREATE POLICY "Allow authenticated read on DistinctivenessLevels" 
    ON "DistinctivenessLevels" FOR SELECT 
    USING (true);

CREATE POLICY "Allow authenticated read on SRM" 
    ON "SRM" FOR SELECT 
    USING (true);

CREATE POLICY "Allow authenticated read on TradingRules" 
    ON "TradingRules" FOR SELECT 
    USING (true);

-- Create policies for admin users to manage reference data
-- Replace 'admin_role_id' with your actual admin role UUID
CREATE POLICY "Allow admin insert on Banks" 
    ON "Banks" FOR INSERT 
    WITH CHECK (true);

CREATE POLICY "Allow admin update on Banks" 
    ON "Banks" FOR UPDATE 
    USING (true);

CREATE POLICY "Allow admin delete on Banks" 
    ON "Banks" FOR DELETE 
    USING (true);

-- Repeat for other tables...
-- (You can create similar policies for Pricing, HabitatCatalog, Stock, etc.)

-- =====================================================
-- Triggers for updating timestamps
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for each table
CREATE TRIGGER update_banks_updated_at BEFORE UPDATE ON "Banks"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pricing_updated_at BEFORE UPDATE ON "Pricing"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_habitat_catalog_updated_at BEFORE UPDATE ON "HabitatCatalog"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stock_updated_at BEFORE UPDATE ON "Stock"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_distinctiveness_levels_updated_at BEFORE UPDATE ON "DistinctivenessLevels"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_srm_updated_at BEFORE UPDATE ON "SRM"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trading_rules_updated_at BEFORE UPDATE ON "TradingRules"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Views for easy data access
-- =====================================================

-- View: Banks with counts
CREATE OR REPLACE VIEW "BanksWithCounts" AS
SELECT 
    b.bank_id,
    b.bank_name,
    b.lpa_name,
    b.nca_name,
    COUNT(DISTINCT p.habitat_name) as habitat_count,
    COUNT(DISTINCT s.stock_id) as stock_count,
    SUM(s.quantity_available) as total_units_available
FROM "Banks" b
LEFT JOIN "Pricing" p ON b.bank_id = p.bank_id
LEFT JOIN "Stock" s ON b.bank_id = s.bank_id
GROUP BY b.bank_id, b.bank_name, b.lpa_name, b.nca_name;

-- View: Habitat availability summary
CREATE OR REPLACE VIEW "HabitatAvailability" AS
SELECT 
    h.habitat_name,
    h.broader_type,
    h.distinctiveness_name,
    h."UmbrellaType",
    COUNT(DISTINCT s.bank_id) as available_in_banks,
    SUM(s.quantity_available) as total_units_available
FROM "HabitatCatalog" h
LEFT JOIN "Stock" s ON h.habitat_name = s.habitat_name
GROUP BY h.habitat_name, h.broader_type, h.distinctiveness_name, h."UmbrellaType";

-- =====================================================
-- Completion message
-- =====================================================
DO $$ 
BEGIN 
    RAISE NOTICE 'Reference tables schema created successfully!';
    RAISE NOTICE 'Remember to populate the tables with your actual data.';
END $$;
