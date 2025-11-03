# Hedgerow On-Site Offsetting Implementation

## Overview
Implemented on-site mitigation for hedgerows with proper trading rules, matching the behavior of habitat units.

## Trading Rules for Hedgerows

As specified, hedgerows follow simpler trading rules than habitat units:

| Distinctiveness | Trading Rule |
|----------------|--------------|
| Very High | Same habitat required (like-for-like) |
| High | Same habitat required (like-for-like) |
| Medium | Same distinctiveness or better habitat required |
| Low | Same distinctiveness or better habitat required |
| Very Low | Same distinctiveness or better habitat required |

**Key difference from habitat units**: No broad group matching needed for hedgerows. Only distinctiveness and habitat name matter.

## Implementation

### 1. Trading Rule Function: `can_offset_hedgerow()`

```python
def can_offset_hedgerow(d_band: str, d_hab: str, s_band: str, s_hab: str) -> bool:
    """
    Check if hedgerow surplus can offset hedgerow deficit.
    
    Args:
        d_band: Deficit distinctiveness (e.g., "Medium")
        d_hab: Deficit habitat name
        s_band: Surplus distinctiveness
        s_hab: Surplus habitat name
    
    Returns:
        True if surplus can offset deficit
    """
    rank = {"Very Low": 0, "Low": 1, "Medium": 2, "High": 3, "Very High": 4}
    
    if d_band == "Very High" or d_band == "High":
        return d_hab == s_hab  # Like-for-like only
    
    # For Medium, Low, Very Low: same distinctiveness or better
    return rank[s_band] >= rank[d_band]
```

### 2. Offset Application Function: `apply_hedgerow_offsets()`

Similar to `apply_area_offsets()` but simpler:
- No broad group considerations
- No priority hierarchy within Medium
- Sorts deficits by distinctiveness only (Very High > High > Medium > Low > Very Low)
- Uses `can_offset_hedgerow()` to determine eligible surpluses

Returns:
- `residual_off_site`: Unmet deficits after on-site offsetting
- `surplus_after_offsets_detail`: Remaining surpluses for headline allocation

### 3. Hedgerow Requirements Calculation

The hedgerow section now follows the same pattern as habitat units:

```python
# Step 1: Apply on-site offsets
hedge_alloc = apply_hedgerow_offsets(hedge_norm)
hedge_residual_table = hedge_alloc["residual_off_site"]
hedge_surplus_detail = hedge_alloc["surplus_after_offsets_detail"]

# Step 2: Parse headline net gain target
hedge_net_gain_requirement = baseline_units * target_percent

# Step 3: Allocate remaining surpluses to headline
# (Try to cover net gain with leftover surpluses)

# Step 4: Calculate headline remainder
# Only add "Net Gain (Hedgerows)" if surplus couldn't cover it
```

## Example Scenarios

### Scenario 1: Surplus Offsets Deficit

**Input:**
- Deficit: 1.0 units of Medium hedgerow
- Surplus: 0.8 units of High hedgerow
- Net gain required: 0.1 units (from 1.0 baseline × 10%)

**Process:**
1. High (0.8) can offset Medium (trading rule: better distinctiveness)
2. 0.8 High offsets 0.8 of the 1.0 Medium deficit → 0.2 residual
3. No surplus left to cover 0.1 net gain

**Output:**
- Native hedgerow (Medium): 0.2 units
- Net Gain (Hedgerows): 0.1 units
- **Total: 0.3 units** ✓

**Previously (without offsetting):**
- Native hedgerow: 1.0 units
- Net Gain (Hedgerows): 0.1 units
- Total: 1.1 units ❌

### Scenario 2: Surplus Covers Everything

**Input:**
- No deficits
- Surplus: 0.5 units of High hedgerow
- Net gain required: 0.1 units

**Process:**
1. No deficits to offset
2. Surplus (0.5) covers net gain (0.1) completely

**Output:**
- (empty - no requirements)
- **Total: 0 units** ✓

### Scenario 3: Very High Requires Like-for-Like

**Input:**
- Deficit: 1.0 units of "Ancient hedgerow A" (Very High)
- Surplus: 0.5 units of "Ancient hedgerow B" (Very High)
- Net gain required: 0.0 units

**Process:**
1. Different habitats, so Cannot offset (trading rule: like-for-like only)
2. Full deficit remains

**Output:**
- Ancient hedgerow A: 1.0 units
- **Total: 1.0 units** ✓

## Consistency with Habitat Units

Both habitat and hedgerow requirements now follow the same pattern:

| Step | Habitat Units | Hedgerow Units |
|------|--------------|----------------|
| 1. Parse Trading Summary | ✓ | ✓ |
| 2. Apply on-site offsets | ✓ Complex rules (broad groups) | ✓ Simple rules (distinctiveness only) |
| 3. Parse headline net gain | ✓ | ✓ |
| 4. Allocate surpluses to headline | ✓ | ✓ |
| 5. Return residual requirements | ✓ | ✓ |

## Files Modified

1. **metric_reader.py**
   - Added `can_offset_hedgerow()` function
   - Added `apply_hedgerow_offsets()` function
   - Updated hedgerow parsing to apply offsets
   - Updated documentation

## Testing

All existing tests pass:
- ✅ `test_baseline_reading.py` - Baseline info parsing
- ✅ `test_hedgerow_watercourse_netgain.py` - Net gain calculations

The implementation correctly handles:
- Surplus offsetting deficits according to trading rules
- Surplus covering net gain requirements
- Like-for-like requirements for Very High/High
- Empty requirements when surplus covers everything
