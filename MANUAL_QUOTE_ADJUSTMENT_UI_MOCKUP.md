# Manual Quote Adjustment UI Mockup

## Overview
This document shows the UI changes for the manual quote adjustment feature.

## 1. Allocation Detail Section (with Remove Buttons)

```
📋 Allocation detail

┌─────────────────────────────────────────────────────────────────────────────┬─────┐
│ demand_habitat | supply_habitat | bank_name | units | price | cost         │ ❌  │
│ Cropland       | Grassland      | Bank A    | 10.5  | £100  | £1,050       │     │
├─────────────────────────────────────────────────────────────────────────────┼─────┤
│ Arable         | Woodland       | Bank B    | 15.0  | £150  | £2,250       │ ❌  │
├─────────────────────────────────────────────────────────────────────────────┼─────┤
│ Scrubland      | Forest         | Bank C    | 8.0   | £120  | £960         │ ❌  │
└─────────────────────────────────────────────────────────────────────────────┴─────┘

Each row has a remove button (❌) that, when clicked, removes that allocation
and updates all totals automatically.
```

## 2. Manual Additions Section Header

```
─────────────────────────────────────────────────────────────────────────────

➕ Manual Additions (Area, Hedgerow & Watercourse)

ℹ️ Add additional area, hedgerow or watercourse units to your quote. 
   These will be included in the final client report.
```

## 3. Manual Area Habitat Entry Section

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 🌳 Manual Area Habitat Units                                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ ┌──────────────┬──────────────┬──────────┬─────────────┬──────────┬──────┐ │
│ │ Habitat Lost │ Habitat to   │ Units    │ Price/Unit  │ Paired   │ 🗑️  │ │
│ │              │ Mitigate     │          │ (£)         │          │      │ │
│ ├──────────────┼──────────────┼──────────┼─────────────┼──────────┼──────┤ │
│ │ [Dropdown]   │ [Dropdown]   │ [Number] │ [Number]    │ [☐]      │      │ │
│ │ Cropland     │ Grassland    │ 10.00    │ 100         │          │      │ │
│ └──────────────┴──────────────┴──────────┴─────────────┴──────────┴──────┘ │
│                                                                              │
│ ┌──────────────┬──────────────┬──────────┬─────────────┬──────────┬──────┐ │
│ │ [Dropdown]   │ [Dropdown]   │ [Number] │ [Number]    │ [☑]      │ 🗑️  │ │
│ │ Arable       │ Woodland     │ 15.00    │ 150         │ Paired   │      │ │
│ └──────────────┴──────────────┴──────────┴─────────────┴──────────┴──────┘ │
│                                                                              │
│ [➕ Add Area Habitat Entry]  [🧹 Clear Area Habitats]                      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 4. Field Descriptions

### Habitat Lost (Dropdown)
- Select the area habitat being lost/impacted
- Populated from catalog's area habitats
- Includes "Net Gain (10%)" option

### Habitat to Mitigate (Dropdown)
- Select the area habitat to provide for mitigation
- Populated from catalog's area habitats
- Includes "Net Gain (10%)" option

### Units (Number Input)
- Number of habitat units required
- Minimum: 0.0
- Step: 0.01

### Price/Unit (£) (Number Input)
- Price per unit in pounds
- Minimum: 0.0
- Step: 1.0

### Paired (Checkbox)
- Check to indicate paired habitat allocation
- When checked, applies 4/3 SRM multiplier automatically
- Effective units = units × (4/3)
- Cost = effective_units × price_per_unit
- Display shows "(Paired)" suffix in reports

### Remove Button (🗑️)
- Removes the entire row
- Immediately updates all calculations

## 5. Buttons

### ➕ Add Area Habitat Entry
- Adds a new blank row for manual entry
- Each row gets a unique ID for tracking

### 🧹 Clear Area Habitats
- Removes all manual area habitat entries at once
- Requires confirmation via rerun

## 6. Similar Sections for Hedgerow & Watercourse

The hedgerow and watercourse sections remain unchanged, matching the existing functionality:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 🌿 Manual Hedgerow Units                                                     │
│ (Same layout as before, without paired checkbox)                            │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ 💧 Manual Watercourse Units                                                  │
│ (Same layout as before, without paired checkbox)                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 7. Updated Summary Display

```
Contract size = Large. 
Subtotal (units): £4,260  |  Admin fee: £500  |  Grand total: £4,760

Note: Totals automatically update based on:
- Remaining allocation rows (after removals)
- Manual hedgerow entries
- Manual watercourse entries  
- Manual area habitat entries (with SRM for paired)
```

## 8. Client Report Impact

In the generated client report, manual entries appear as:

```
AREA HABITATS
┌─────────────────┬───────────────┬────────┬────────────────┬──────────────────────┐
│ Distinctiveness │ Habitats Lost │ Units  │ Supply Dist    │ Habitats Supplied    │
├─────────────────┼───────────────┼────────┼────────────────┼──────────────────────┤
│ Medium          │ Cropland      │ 10.00  │ Medium         │ Grassland            │
│ Medium          │ Arable        │ 15.00  │ High           │ Woodland (Paired)    │
└─────────────────┴───────────────┴────────┴────────────────┴──────────────────────┘

Note: "(Paired)" suffix automatically added for paired allocations
Effective units shown in "Supply Units" column (15.00 → 20.00 with SRM)
```

## 9. Interaction Flow

1. **User runs optimization** → Results appear in allocation detail
2. **User reviews allocations** → Clicks ❌ on unwanted rows
3. **Totals update automatically** → Shows new subtotal
4. **User scrolls to Manual Additions** → Sees all three sections (Area, Hedgerow, Watercourse)
5. **User clicks "➕ Add Area Habitat Entry"** → New blank row appears
6. **User fills in fields** → Selects habitats, enters units and price
7. **User checks "Paired" if needed** → System applies SRM automatically
8. **User clicks "Generate Report"** → All manual entries and removals reflected in report

## 10. State Persistence

All changes persist across:
- Page refreshes (reruns)
- Map interactions
- Navigation between sections
- Report generation

Until "🔄 Start New Quote" is clicked, which resets everything.

## Visual Design Notes

- Remove buttons (❌) are red/danger colored
- Add buttons (➕) are primary/blue colored
- Clear buttons (🧹) are secondary colored
- Paired checkbox has a distinct style when checked
- All number inputs have appropriate step values
- Dropdowns are searchable for easier habitat selection
- Container borders distinguish each section clearly
- Icons provide visual cues for actions
