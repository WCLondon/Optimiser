-- New promoter tables schema
-- Replaces the old introducers table with separate tables for companies and individuals

-- Promoter Companies Table
-- Stores company/organization promoters
CREATE TABLE IF NOT EXISTS promoter_companies (
    id SERIAL PRIMARY KEY,
    company_name TEXT NOT NULL UNIQUE,
    username TEXT UNIQUE,
    password_hash TEXT,
    password_salt TEXT,
    contact_person TEXT,
    email TEXT,
    phone TEXT,
    address TEXT,
    discount_type TEXT NOT NULL CHECK(discount_type IN ('tier_up', 'percentage', 'no_discount')),
    discount_value FLOAT NOT NULL DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_date TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Promoter Individuals Table
-- Stores individual promoters
CREATE TABLE IF NOT EXISTS promoter_individuals (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    username TEXT UNIQUE,
    password_hash TEXT,
    password_salt TEXT,
    email TEXT,
    phone TEXT,
    parent_company_id INTEGER REFERENCES promoter_companies(id),
    discount_type TEXT NOT NULL CHECK(discount_type IN ('tier_up', 'percentage', 'no_discount')),
    discount_value FLOAT NOT NULL DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_date TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_promoter_companies_username ON promoter_companies(username);
CREATE INDEX IF NOT EXISTS idx_promoter_companies_email ON promoter_companies(email);
CREATE INDEX IF NOT EXISTS idx_promoter_individuals_username ON promoter_individuals(username);
CREATE INDEX IF NOT EXISTS idx_promoter_individuals_email ON promoter_individuals(email);
CREATE INDEX IF NOT EXISTS idx_promoter_individuals_parent ON promoter_individuals(parent_company_id);

-- Comments for documentation
COMMENT ON TABLE promoter_companies IS 'Stores company/organization promoters with login credentials';
COMMENT ON TABLE promoter_individuals IS 'Stores individual promoters, optionally linked to a parent company';
COMMENT ON COLUMN promoter_companies.discount_type IS 'Type of discount: tier_up, percentage, or no_discount';
COMMENT ON COLUMN promoter_individuals.parent_company_id IS 'Optional reference to parent company for individual promoters';
