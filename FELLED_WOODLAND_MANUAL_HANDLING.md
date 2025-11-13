# Felled Woodland Special Handling

## Overview

The app now includes special handling for 'Woodland and forest - Felled/Replacement for felled woodland' to prevent it from being matched with other habitats like Lowland Mixed Deciduous through the optimizer.

## Problem

'Woodland and forest - Felled/Replacement for felled woodland' was being matched with 'Woodland and forest - Lowland mixed deciduous woodland' or other compatible habitats through paired allocations or trading rules. This is incorrect - Felled woodland should be sold as its own habitat with user-specified pricing.

## Solution

The app now **always** intercepts Felled Woodland demands before optimization and handles them as manual entries with user-provided pricing, regardless of whether stock or trading rules exist.

## How It Works

### Detection (app.py)
1. Before running optimization, the app checks if 'Woodland and forest - Felled/Replacement for felled woodland' is in the demand
2. If present, special handling is **always** triggered (no stock check)
3. The habitat is removed from the demand that goes to the optimizer

### User Interaction (app.py only)
When Felled Woodland is detected:
1. A warning message is displayed: "⚠️ 'Woodland and forest - Felled/Replacement for felled woodland' requires off-site mitigation with manual pricing."
2. For each Felled Woodland demand, a form appears asking for the price per unit
3. Default value is set to £15,000 per unit (can be adjusted)
4. User must click "Set Price and Continue" to proceed

### Automatic Processing
Once the price is provided:
1. The habitat is automatically added to manual area entries
2. It's removed from the demand that goes to the optimizer
3. A success message confirms: "✅ Added X Felled Woodland entries as manual allocations"
4. Optimization proceeds with remaining habitats (NOT including Felled Woodland)

### Promoter App Rejection (promoter_app.py)
In the automated promoter workflow:
1. Checks if Felled Woodland is in the metric file
2. If found, displays error: "❌ 'Woodland and forest - Felled/Replacement for felled woodland' is not supported in automated quote generation."
3. Suggests: "This habitat requires manual pricing. Please use the main app (app.py) instead."
4. Stops processing

### Integration with Manual Entries
The Felled Woodland entry is treated exactly like a user-added manual entry:
- Appears in the "Manual Additions" section
- Included in allocation details
- Included in client report table
- Contributes to total cost calculations

## Key Changes from Previous Version

**Previous behavior (INCORRECT):**
- Only intercepted if no stock existed
- If stock or trading rules existed, optimizer would match with Lowland Mixed Deciduous
- Could result in paired allocations with other habitats

**Current behavior (CORRECT):**
- **Always** intercepts Felled Woodland, regardless of stock/trading rules
- **Never** allows optimizer to match it with any other habitat
- **Always** requires manual pricing from user
- Completely prevents paired allocations or substitutions

## User Experience Flow

### Main App (app.py)
```
1. User adds demands including Felled Woodland
2. User clicks "Optimise now"
3. App ALWAYS detects Felled Woodland (no stock check)
4. Form appears: "Please provide unit price for X units"
5. User enters price (e.g., £15,000)
6. User clicks "Set Price and Continue"
7. Success message: "Added 1 Felled Woodland entry"
8. Optimization runs ONLY for remaining habitats
9. Results show optimized allocations + manual Felled Woodland entry
10. NO Lowland Mixed Deciduous or paired allocations for Felled Woodland
```

### Promoter App (promoter_app.py)
```
1. User uploads metric file with Felled Woodland
2. App detects Felled Woodland in parsed demands
3. Error displayed: "Not supported in automated quote generation"
4. Process stops - user must use main app instead
```

## Technical Details

### Session State Variables (app.py)
- `felled_woodland_price_per_unit`: Dictionary storing prices for each Felled Woodland demand
  - Key format: `fw_{idx}` where idx is the demand row index
  - Value: Price per unit in pounds
  - Cleared on quote reset

### Manual Entry Structure
```python
{
    "id": <auto-incremented ID>,
    "habitat_lost": "Woodland and forest - Felled/Replacement for felled woodland",
    "habitat_name": "Woodland and forest - Felled/Replacement for felled woodland",
    "units": <units required>,
    "price_per_unit": <user-provided price>,
    "paired": False
}
```

### Code Locations
- **app.py**: Lines ~4327-4395 (before optimization call)
  - Triggers: **Always** when Felled Woodland is in demand
  - Behavior: Prompt for price, add as manual entry, remove from optimizer
- **promoter_app.py**: Lines ~427-434 (after parsing metric)
  - Triggers: When Felled Woodland is in parsed demand
  - Behavior: Show error and stop

## Benefits

1. **Correct Behavior**: Felled Woodland is never matched with Lowland Mixed Deciduous
2. **No Confusion**: Always sold as its own habitat, not as a substitute
3. **Flexible Pricing**: Admin can set appropriate price for each case
4. **Clear Communication**: User understands what's happening at each step
5. **Automatic**: Once price is set, everything else is handled automatically
6. **Protected Workflow**: Promoter app explicitly rejects it to maintain data integrity

## Scope

- ✅ **app.py**: Full interactive handling with user prompts
- ✅ **promoter_app.py**: Explicit rejection with helpful error message

This ensures Felled Woodland is **always** handled correctly in both workflows:
- Main app: Interactive manual pricing
- Promoter app: Rejected with clear guidance

## Example Scenarios

### Scenario 1: Main App (app.py)
**Demand**: 2.5 units of 'Woodland and forest - Felled/Replacement for felled woodland'

**Previous behavior (INCORRECT)**:
- Optimizer found paired allocation with Lowland Mixed Deciduous
- Client received Lowland Mixed Deciduous + Grassland instead

**Current behavior (CORRECT)**:
1. Form asks: "Price per unit (£) for 2.5 units:"
2. User enters: £16,000
3. Manual entry created: 2.5 units @ £16,000 = £40,000
4. Optimizer runs ONLY for other habitats
5. Final quote includes ONLY the £40,000 Felled Woodland allocation (no substitutions)

### Scenario 2: Promoter App (promoter_app.py)
**Demand**: Metric file includes Felled Woodland

**Behavior**:
1. App parses metric file
2. Detects Felled Woodland in demands
3. Shows error: "Not supported in automated quote generation"
4. Suggests using main app
5. Processing stops

## Future Enhancements

If more habitats need similar special handling, this pattern can be extended:
- Add habitat names to a list of special habitats
- Loop through them before optimization
- Each can have its own pricing form and logic
