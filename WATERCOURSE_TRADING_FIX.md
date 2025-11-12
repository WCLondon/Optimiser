# Watercourse Trading Rules Fix

## Summary
This fix ensures that Medium distinctiveness watercourse habitats like canals and ditches cannot mitigate for one another during optimization, as required by BNG trading rules.

## Changes

### Files Modified
1. **optimizer_core.py** - Updated `enforce_watercourse_rules` function
2. **app.py** - Updated `enforce_watercourse_rules` function  
3. **test_canals_ditches_trading.py** - New test to verify the fix

### Key Implementation
Added habitat normalization logic to identify different watercourse types:
- Rivers/streams
- Canals
- Ditches
- Culverts
- Priority habitats

### Trading Rules Enforced
- **Very High**: Not eligible for normal trading (bespoke compensation required)
- **High**: Same habitat required (like-for-like)
- **Medium**: Same habitat required (like-for-like) ← **KEY FIX**
- **Low**: Must trade to better distinctiveness AND same habitat

## Testing
All existing tests pass:
- ✅ test_watercourse_trading_rules.py
- ✅ test_watercourse_on_site_mitigation.py
- ✅ test_watercourse_net_gain_low_medium.py
- ✅ test_ditches_simple.py

New test verifies:
- ✅ Canals cannot offset Ditches
- ✅ Ditches cannot offset Canals
- ✅ Same habitat trading still works
- ✅ Higher distinctiveness doesn't override habitat matching
