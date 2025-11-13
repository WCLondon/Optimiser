# Felled Woodland Special Handling

## Overview

The app now includes special handling for 'Woodland and forest - Felled/Replacement for felled woodland' to address cases where this habitat is required but no stock is available.

## Problem

When 'Woodland and forest - Felled/Replacement for felled woodland' appears in demand but there's no stock available in any bank, the optimizer would normally fail with "No legal options" error.

## Solution

The app now automatically detects this situation and prompts the user for a manual unit price, then handles it as an off-site manual allocation.

## How It Works

### Detection
1. Before running optimization, the app checks if 'Woodland and forest - Felled/Replacement for felled woodland' is in the demand
2. It then checks if there's any stock available for this habitat in the Stock table
3. If no stock is available, special handling is triggered

### User Interaction
When no stock is available:
1. A warning message is displayed: "⚠️ 'Woodland and forest - Felled/Replacement for felled woodland' requires off-site mitigation with manual pricing."
2. For each Felled Woodland demand, a form appears asking for the price per unit
3. Default value is set to £15,000 per unit (can be adjusted)
4. User must click "Set Price and Continue" to proceed

### Automatic Processing
Once the price is provided:
1. The habitat is automatically added to manual area entries
2. It's removed from the demand that goes to the optimizer
3. A success message confirms: "✅ Added X Felled Woodland entries as manual allocations"
4. Optimization proceeds with remaining habitats

### Integration with Manual Entries
The Felled Woodland entry is treated exactly like a user-added manual entry:
- Appears in the "Manual Additions" section
- Included in allocation details
- Included in client report table
- Contributes to total cost calculations

## User Experience Flow

```
1. User adds demands including Felled Woodland
2. User clicks "Optimise now"
3. App detects no stock for Felled Woodland
4. Form appears: "Please provide unit price for X units"
5. User enters price (e.g., £15,000)
6. User clicks "Set Price and Continue"
7. Success message: "Added 1 Felled Woodland entry"
8. Optimization runs for remaining habitats
9. Results show both optimized allocations and manual Felled Woodland entry
```

## Technical Details

### Session State Variables
- `felled_woodland_price_per_unit`: Dictionary storing prices for each Felled Woodland demand
  - Key format: `fw_{idx}` where idx is the demand row index
  - Value: Price per unit in pounds

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

### Code Location
- File: `app.py`
- Lines: ~4327-4393 (before optimization call)
- Triggers: When 'Woodland and forest - Felled/Replacement for felled woodland' is in demand AND no stock exists

## Benefits

1. **No Error**: Users don't see confusing "No legal options" errors
2. **Flexible Pricing**: Admin can set appropriate price for each case
3. **Seamless Integration**: Works with existing manual entry system
4. **Clear Communication**: User understands what's happening at each step
5. **Automatic**: Once price is set, everything else is handled automatically

## Scope

- **Applies to**: app.py only (main application)
- **Does NOT apply to**: promoter_app.py (automated quote generation)

This allows the main app to handle special cases interactively while keeping the promoter app simpler for automated workflows.

## Example Scenario

**Demand**: 2.5 units of 'Woodland and forest - Felled/Replacement for felled woodland'

**Stock**: None available in any bank

**Result**:
1. Form asks: "Price per unit (£) for 2.5 units:"
2. User enters: £16,000
3. Manual entry created: 2.5 units @ £16,000 = £40,000
4. Optimization proceeds with other habitats
5. Final quote includes the £40,000 Felled Woodland allocation

## Future Enhancements

If more habitats need similar special handling, this pattern can be extended:
- Add habitat names to a list of special habitats
- Loop through them before optimization
- Each can have its own pricing form and logic
