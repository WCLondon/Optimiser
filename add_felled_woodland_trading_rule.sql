-- SQL Script: Add Trading Rule for Felled Woodland
-- 
-- Purpose: Allow 'Woodland and forest - Felled/Replacement for felled woodland' 
--          to be matched with 'Woodland and forest - Lowland mixed deciduous woodland' supply
--
-- Background:
-- Both habitats are High distinctiveness. By default, High distinctiveness habitats
-- require exact habitat matching. This trading rule explicitly allows Felled woodland
-- demand to be satisfied by Lowland mixed deciduous woodland supply.
--
-- Issue Reference: Felled Woodland / Lowland Mixed Deciduous
--
-- Prerequisites:
-- 1. Both habitats must exist in the HabitatCatalog table
-- 2. TradingRules table must exist (created during database setup)
--
-- Verification Query (run BEFORE applying this script):
-- SELECT habitat_name, broader_type, distinctiveness_name, "UmbrellaType"
-- FROM "public"."HabitatCatalog"
-- WHERE habitat_name IN (
--     'Woodland and forest - Felled/Replacement for felled woodland',
--     'Woodland and forest - Lowland mixed deciduous woodland'
-- );
--
-- Expected result: Both habitats should be present with High distinctiveness
--

-- Insert the trading rule
INSERT INTO "public"."TradingRules" (
    "demand_habitat",
    "allowed_supply_habitat",
    "min_distinctiveness_name",
    "companion_habitat"
)
VALUES (
    'Woodland and forest - Felled/Replacement for felled woodland',
    'Woodland and forest - Lowland mixed deciduous woodland',
    NULL,  -- No minimum distinctiveness requirement (both are already High)
    NULL   -- No companion habitat required
)
ON CONFLICT DO NOTHING;  -- Prevent duplicate entries if rule already exists

-- Verification Query (run AFTER applying this script):
-- SELECT * FROM "public"."TradingRules"
-- WHERE demand_habitat = 'Woodland and forest - Felled/Replacement for felled woodland';
--
-- Expected result: One row showing the trading rule

-- Test the trading rule with a sample optimization:
-- After applying this rule, when the optimizer receives demand for 
-- 'Woodland and forest - Felled/Replacement for felled woodland',
-- it will be able to use 'Woodland and forest - Lowland mixed deciduous woodland' 
-- from any bank that has it in stock, subject to normal pricing and tier calculations.
