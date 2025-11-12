# Felled Woodland / Lowland Mixed Deciduous Trading Implementation

## Issue Summary

The optimizer needs to treat 'Woodland and forest - Felled/Replacement for felled woodland' like 'Woodland and forest - Lowland mixed deciduous woodland' when optimizing and finding suitable trades.

## Background

Both habitats are:
- **Broader Type**: Woodland and forest
- **Distinctiveness**: High
- **UmbrellaType**: Area Habitat

By default, the optimizer requires **exact habitat matching** for High distinctiveness habitats. This means:
- Felled woodland demand can only be matched with Felled woodland supply
- Lowland mixed deciduous demand can only be matched with Lowland mixed deciduous supply

However, ecologically, Felled/Replacement woodland should be able to use Lowland mixed deciduous woodland as supply, since replacement woodland is typically planted as mixed deciduous.

## Solution

The optimizer already has full support for **Trading Rules** - a database table that defines explicit habitat substitutions. No code changes are required.

### Database Change Required

Add a single row to the `TradingRules` table:

```sql
INSERT INTO "public"."TradingRules" (
    "demand_habitat",
    "allowed_supply_habitat",
    "min_distinctiveness_name",
    "companion_habitat"
)
VALUES (
    'Woodland and forest - Felled/Replacement for felled woodland',
    'Woodland and forest - Lowland mixed deciduous woodland',
    NULL,
    NULL
);
```

### How It Works

1. **Without Trading Rule** (Current Behavior):
   - Demand: Felled woodland (2.5 units)
   - Available Supply: Lowland mixed deciduous (10.0 units)
   - Result: ❌ NO MATCH (both are High distinctiveness, exact match required)
   - Optimizer will fail or look for exact Felled woodland supply

2. **With Trading Rule** (Fixed Behavior):
   - Demand: Felled woodland (2.5 units)
   - Available Supply: Lowland mixed deciduous (10.0 units)
   - Trading Rule: ✓ Allows Felled → Lowland mixed deciduous
   - Result: ✅ MATCH FOUND
   - Optimizer allocates 2.5 units of Lowland mixed deciduous to satisfy Felled demand

### Technical Details

The trading rule logic in `optimizer_core.py` (lines 1948-1970):

```python
if "TradingRules" in backend and dem_hab in set(backend["TradingRules"]["demand_habitat"]):
    explicit = True
    for _, rule in backend["TradingRules"][backend["TradingRules"]["demand_habitat"] == dem_hab].iterrows():
        sh = sstr(rule["allowed_supply_habitat"])
        # Find stock matching the allowed supply habitat
        df_s = stock_full[stock_full["habitat_name"] == sh].copy()
        if not df_s.empty: 
            cand_parts.append(df_s)
```

When a trading rule exists:
1. The optimizer marks it as an "explicit" rule
2. Only the specified `allowed_supply_habitat` is considered
3. Optional `min_distinctiveness_name` can enforce minimum quality
4. Normal tier calculation (local/adjacent/far) still applies
5. Normal pricing rules still apply

## Implementation Steps

### 1. Prerequisites Check

Verify both habitats exist in HabitatCatalog:

```sql
SELECT habitat_name, broader_type, distinctiveness_name, "UmbrellaType"
FROM "public"."HabitatCatalog"
WHERE habitat_name IN (
    'Woodland and forest - Felled/Replacement for felled woodland',
    'Woodland and forest - Lowland mixed deciduous woodland'
);
```

Expected: 2 rows, both with High distinctiveness

### 2. Apply SQL Script

Run the provided SQL script:
```bash
psql -h <host> -U <user> -d <database> -f add_felled_woodland_trading_rule.sql
```

Or execute via Admin Dashboard/Database Tool:
```sql
INSERT INTO "public"."TradingRules" (
    "demand_habitat",
    "allowed_supply_habitat",
    "min_distinctiveness_name",
    "companion_habitat"
)
VALUES (
    'Woodland and forest - Felled/Replacement for felled woodland',
    'Woodland and forest - Lowland mixed deciduous woodland',
    NULL,
    NULL
)
ON CONFLICT DO NOTHING;
```

### 3. Verification

Check the trading rule was added:

```sql
SELECT * FROM "public"."TradingRules"
WHERE demand_habitat = 'Woodland and forest - Felled/Replacement for felled woodland';
```

Expected: 1 row showing the trading rule

### 4. Testing

Run the automated test:

```bash
cd /home/runner/work/Optimiser/Optimiser
python test_felled_woodland_trading.py
```

Expected output:
```
✅ ALL TESTS PASSED!

Conclusion:
  The TradingRules table entry is REQUIRED for Felled woodland to trade
  with Lowland mixed deciduous woodland, because both are High distinctiveness
  and High distinctiveness requires exact matching by default.
```

### 5. Manual Testing

1. Open the app (app.py or promoter_app.py)
2. Create a quote with Felled woodland demand
3. Run optimizer
4. Verify that Lowland mixed deciduous supply is allocated

## Files Created/Modified

### New Files
- `test_felled_woodland_trading.py` - Comprehensive test demonstrating the trading rule
- `add_felled_woodland_trading_rule.sql` - SQL script to add the trading rule
- `FELLED_WOODLAND_TRADING_IMPLEMENTATION.md` - This documentation

### No Code Changes Required
- `optimizer_core.py` - Already has full TradingRules support (no changes needed)
- `app.py` - No changes needed
- `promoter_app.py` - No changes needed

## Testing Results

The test `test_felled_woodland_trading.py` demonstrates:

1. **Test 1: WITH Trading Rule** ✅
   - Felled woodland demand can be matched with Lowland mixed deciduous supply
   - Options are generated correctly
   - Pricing and tier calculation work as expected

2. **Test 2: WITHOUT Trading Rule** ✅  
   - Felled woodland demand CANNOT be matched with Lowland mixed deciduous supply
   - Demonstrates why the trading rule is necessary
   - Confirms default High distinctiveness behavior

## Impact Analysis

### What Changes
- Felled woodland demand can now be satisfied by Lowland mixed deciduous supply
- Optimizer will find valid allocations where it previously failed

### What Doesn't Change
- All other habitat trading rules remain unchanged
- Pricing calculations unchanged
- Tier calculations (local/adjacent/far) unchanged
- Other High distinctiveness habitats still require exact matching (unless they have their own trading rules)

### Edge Cases
- If both Felled and Lowland mixed deciduous supply exist, optimizer chooses based on cost
- Trading rule is one-way: Lowland mixed deciduous DEMAND still requires exact match (unless you add a reverse rule)
- Rule applies across all banks - any bank with Lowland mixed deciduous stock can satisfy Felled demand

## Rollback Plan

If needed, remove the trading rule:

```sql
DELETE FROM "public"."TradingRules"
WHERE demand_habitat = 'Woodland and forest - Felled/Replacement for felled woodland'
  AND allowed_supply_habitat = 'Woodland and forest - Lowland mixed deciduous woodland';
```

The optimizer will immediately revert to requiring exact habitat matches for Felled woodland.

## Future Enhancements

If additional woodland substitutions are needed, add more trading rules:

```sql
-- Example: Allow other woodland types as substitutes
INSERT INTO "public"."TradingRules" (demand_habitat, allowed_supply_habitat)
VALUES 
    ('Woodland and forest - Felled/Replacement for felled woodland', 'Woodland and forest - Upland mixed ashwoods'),
    ('Woodland and forest - Felled/Replacement for felled woodland', 'Woodland and forest - Upland oakwood');
```

## References

- Issue: "Felled Woodland / Lowland Mixed Deciduous"
- Code: `optimizer_core.py` lines 1948-1970 (Trading Rules logic)
- Database: `TradingRules` table schema in `supabase_schema.sql`
- Test: `test_felled_woodland_trading.py`

## Support

For questions or issues:
1. Check test passes: `python test_felled_woodland_trading.py`
2. Verify trading rule exists in database
3. Check both habitats exist in HabitatCatalog
4. Review optimizer debug output in Admin Dashboard
