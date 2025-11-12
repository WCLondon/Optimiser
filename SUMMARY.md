# Summary: Felled Woodland Trading Rule Implementation

## Problem
The optimizer needed to treat 'Woodland and forest - Felled/Replacement for felled woodland' like 'Woodland and forest - Lowland mixed deciduous woodland' when finding suitable trades.

## Root Cause
Both habitats are High distinctiveness. The optimizer requires **exact habitat matching** for High distinctiveness by default (for ecological accuracy). This meant Felled woodland demand could only be matched with Felled woodland supply, not Lowland mixed deciduous supply.

## Solution
✅ **No code changes required!** The optimizer already has full TradingRules support.

Added a single database record to explicitly allow this substitution:

```sql
INSERT INTO "TradingRules" (demand_habitat, allowed_supply_habitat)
VALUES (
    'Woodland and forest - Felled/Replacement for felled woodland',
    'Woodland and forest - Lowland mixed deciduous woodland'
);
```

## Why This Works
The TradingRules table (implemented in `optimizer_core.py` lines 1948-1970) allows explicit habitat substitutions. When a trading rule exists:
1. The optimizer marks it as an "explicit" rule
2. Only the specified `allowed_supply_habitat` is considered for that demand
3. Normal tier calculation (local/adjacent/far) still applies
4. Normal pricing still applies

## Files Added
- `test_felled_woodland_trading.py` - Comprehensive test (✅ passes)
- `add_felled_woodland_trading_rule.sql` - SQL script for database update
- `FELLED_WOODLAND_TRADING_IMPLEMENTATION.md` - Full documentation

## Testing
✅ New test passes demonstrating:
  - WITH rule: Felled demand matches Lowland deciduous supply
  - WITHOUT rule: High distinctiveness requires exact match

✅ All existing tests pass:
  - test_area_habitat_offsetting.py
  - test_medium_hierarchy.py  
  - test_watercourse_trading_rules.py
  - test_hedgerow_watercourse_netgain.py

✅ CodeQL security scan: No alerts

## Implementation
Admin needs to run the SQL script against the database:

```bash
psql -h <host> -U <user> -d <database> -f add_felled_woodland_trading_rule.sql
```

## Rollback
If needed, remove the trading rule:

```sql
DELETE FROM "TradingRules"
WHERE demand_habitat = 'Woodland and forest - Felled/Replacement for felled woodland';
```

## Impact
- Felled woodland quotes that previously failed will now succeed
- Uses existing Lowland mixed deciduous supply from banks
- All other habitat trading rules unchanged
- Zero risk to existing functionality (no code changes)

## Key Benefits
1. **Zero Code Risk** - No changes to optimizer logic
2. **Easily Reversible** - Single database record can be deleted
3. **Well Tested** - Comprehensive test suite included
4. **Fully Documented** - Implementation guide provided
5. **Security Verified** - CodeQL scan passed

## Next Steps
1. Admin reviews PR
2. Admin applies SQL script to database
3. Admin tests with real Felled woodland demand
4. If successful, close issue
5. If issues, rollback is a single DELETE statement
