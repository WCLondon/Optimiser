# Visual Example: Quote Table Before & After Changes

## Before the Change

When a paired allocation was used (e.g., "Traditional Orchard + Mixed Scrub"), the quote table displayed:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     Development Impact | Mitigation from Wild Capital       │
├──────────────────┬──────────────┬──────────────┬──────────────┬────────────┤
│ Distinctiveness  │ Habitats Lost│  # Units     │ Habitats     │ # Units    │
│                  │              │              │ Supplied     │ Supplied   │
├──────────────────┼──────────────┼──────────────┼──────────────┼────────────┤
│ Medium           │ Grassland    │ 0.14         │ Traditional  │ 0.07       │
│                  │              │              │ Orchard +    │            │
│                  │              │              │ Mixed Scrub  │            │
└──────────────────┴──────────────┴──────────────┴──────────────┴────────────┘
```

**Issues:**
- Shows both habitats in the paired allocation
- Distinctiveness column shows "Medium" (for the demand habitat)
- Not clear which habitat's distinctiveness is being referenced
- Confusing for clients to understand

---

## After the Change

With the new implementation, the same paired allocation now displays:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     Development Impact | Mitigation from Wild Capital       │
├──────────────────┬──────────────┬──────────────┬──────────────┬────────────┤
│ Distinctiveness  │ Habitats Lost│  # Units     │ Habitats     │ # Units    │
│                  │              │              │ Supplied     │ Supplied   │
├──────────────────┼──────────────┼──────────────┼──────────────┼────────────┤
│ Medium           │ Grassland    │ 0.14         │ Traditional  │ 0.07       │
│                  │              │              │ Orchard      │            │
│                  │              │              │ (Medium)     │            │
└──────────────────┴──────────────┴──────────────┴──────────────┴────────────┘
```

**Improvements:**
✅ Shows only the habitat with the highest distinctiveness (Traditional Orchard = Medium)
✅ Mixed Scrub (Low distinctiveness) is not shown
✅ Clearer, more concise information for clients
✅ Distinctiveness is properly attributed to the displayed habitat

---

## Example Scenarios

### Scenario 1: Medium vs Low
**Paired Allocation:** Traditional Orchard (Medium) + Mixed Scrub (Low)
**Displayed:** Traditional Orchard (Medium) ← Higher distinctiveness

### Scenario 2: High vs Medium
**Paired Allocation:** Woodland (High) + Grassland (Medium)
**Displayed:** Woodland (High) ← Higher distinctiveness

### Scenario 3: Very High vs High
**Paired Allocation:** Wetland (Very High) + Woodland (High)
**Displayed:** Wetland (Very High) ← Higher distinctiveness

### Scenario 4: Order Doesn't Matter
**Paired Allocation:** Mixed Scrub (Low) + Traditional Orchard (Medium)
**Displayed:** Traditional Orchard (Medium) ← Higher distinctiveness
*(Same result regardless of order in the paired string)*

---

## Technical Details

### Detection Logic
- Paired allocations are identified by the presence of " + " in the supply_habitat string
- Example: `"Traditional Orchard + Mixed Scrub"` → Parsed into `["Traditional Orchard", "Mixed Scrub"]`

### Selection Logic
Each habitat's distinctiveness is looked up from the catalog and assigned a priority:
1. Very High / V.High (priority 0) ← Highest
2. High (priority 1)
3. Medium (priority 2)
4. Low + 10% Net Gain (priority 3)
5. Low (priority 4)
6. 10% Net Gain (priority 5)
7. Very Low / V.Low (priority 6) ← Lowest

The habitat with the lowest priority number (highest distinctiveness) is selected.

### Pricing Impact
**None.** All pricing, costs, and unit calculations remain exactly as they were:
- Unit prices are unchanged
- Blended prices for paired allocations are unchanged
- Total costs remain the same
- Units supplied remain the same

This is purely a **display change** to improve clarity in the quote table.

---

## What Doesn't Change

✅ Optimization logic (how paired allocations are created)
✅ Pricing calculations (blended prices, unit prices, costs)
✅ Unit allocation (units supplied, effective units)
✅ Non-paired allocations (work exactly as before)
✅ Manual entries (hedgerow/watercourse additions)
✅ All other quote table sections

---

## Real-World Benefit

**For Clients:**
- Clearer understanding of what habitat they're getting
- Focus on the most important (highest distinctiveness) habitat
- Less confusion about paired allocations
- Professional, concise quote presentation

**For Wild Capital:**
- Better client communication
- Reduced need for explanation
- Maintains all internal accuracy and calculations
- No risk to financial data or pricing
