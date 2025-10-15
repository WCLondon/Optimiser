# Quote Table Display - Before and After

## Before This Fix

When the optimiser created a paired allocation, the quote table would show:

```
┌────────────────────┬──────────────────────────────────────┬──────────┐
│ Distinctiveness    │ Habitats Supplied                    │ # Units  │
├────────────────────┼──────────────────────────────────────┼──────────┤
│ Medium             │ Traditional Orchard + Mixed Scrub    │ 0.14     │
└────────────────────┴──────────────────────────────────────┴──────────┘
```

**Problems:**
- Shows concatenated habitat names with "+"
- Distinctiveness shown may be incorrect (not consistently the highest)
- Confusing for clients to understand which habitat is being used

## After This Fix

Now the quote table shows:

```
┌────────────────────┬──────────────────────────────────────┬──────────┐
│ Distinctiveness    │ Habitats Supplied                    │ # Units  │
├────────────────────┼──────────────────────────────────────┼──────────┤
│ High               │ Traditional Orchard                  │ 0.14     │
└────────────────────┴──────────────────────────────────────┴──────────┘
```

**Improvements:**
- Shows only the habitat with the highest distinctiveness
- Distinctiveness is correctly shown as "High" (Traditional Orchard's distinctiveness)
- Clear and unambiguous for clients

## How It Works

The system:
1. Detects paired allocations automatically
2. Extracts both habitats from the pairing
3. Looks up each habitat's distinctiveness level
4. Compares the distinctiveness values (e.g., Very High=8, High=6, Medium=4, Low=2)
5. Displays only the habitat with the highest value

## More Examples

### Example 1: Woodland + Grassland
**Before:** "Woodland + Grassland" (Medium)
**After:** "Woodland" (Very High)

### Example 2: Mixed Scrub + Grassland  
**Before:** "Mixed Scrub + Grassland" (Low)
**After:** "Mixed Scrub" (Medium)

## What Hasn't Changed

✅ **Pricing** - All prices remain exactly the same
✅ **Costs** - Total costs are unchanged
✅ **Optimization** - The optimizer still creates paired allocations when they're cheaper
✅ **Units** - Unit calculations remain the same
✅ **Allocation logic** - How allocations are made hasn't changed

This is purely a **display change** for the quote table to make it clearer and more accurate for clients.
