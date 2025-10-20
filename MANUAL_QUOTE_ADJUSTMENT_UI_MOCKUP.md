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

### Simple (Non-Paired) Mode

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
└──────────────────────────────────────────────────────────────────────────────┘
```

### Paired Mode (When checkbox is ticked)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 🌳 Manual Area Habitat Units                                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ Entry 1 (Paired Allocation)                                                 │
│                                                                              │
│ ┌──────────────────────────────┬──────────────────────────┬──────────────┐ │
│ │ Habitat Lost                 │ Units Required           │              │ │
│ ├──────────────────────────────┼──────────────────────────┼──────────────┤ │
│ │ [Dropdown]                   │ [Number]                 │ 🗑️          │ │
│ │ Cropland                     │ 15.00                    │              │ │
│ └──────────────────────────────┴──────────────────────────┴──────────────┘ │
│                                                                              │
│ Demand Habitat:                                                              │
│ ┌───────────────────────┬────────────────────┬──────────────────────────┐  │
│ │ Habitat Type          │ Bank               │ Price/Unit (£)           │  │
│ ├───────────────────────┼────────────────────┼──────────────────────────┤  │
│ │ [Dropdown]            │ [Dropdown]         │ [Number]                 │  │
│ │ Woodland - mixed      │ Bank A             │ 150                      │  │
│ └───────────────────────┴────────────────────┴──────────────────────────┘  │
│                                                                              │
│ Companion Habitat:                                                           │
│ ┌───────────────────────┬────────────────────┬──────────────────────────┐  │
│ │ Habitat Type          │ Bank               │ Price/Unit (£)           │  │
│ ├───────────────────────┼────────────────────┼──────────────────────────┤  │
│ │ [Dropdown]            │ [Dropdown]         │ [Number]                 │  │
│ │ Grassland             │ Bank B             │ 80                       │  │
│ └───────────────────────┴────────────────────┴──────────────────────────┘  │
│                                                                              │
│ ┌───────────────────┬───────────────────────┬────────────────────────────┐ │
│ │ SRM Tier          │ Demand Stock Use      │ Companion Stock Use        │ │
│ ├───────────────────┼───────────────────────┼────────────────────────────┤ │
│ │ [Dropdown]        │ [Number]              │ 0.40 (auto-calculated)     │ │
│ │ adjacent          │ 0.60                  │                            │ │
│ └───────────────────┴───────────────────────┴────────────────────────────┘ │
│                                                                              │
│ ℹ️ Calculation: SRM = 1.33 | Demand: 9.00 units × £150 = £1,350 |          │
│    Companion: 6.00 units × £80 = £480 | Total: £1,830                       │
│                                                                              │
│ [✓] Paired Entry    (uncheck to switch to simple mode)                      │
│ ───────────────────────────────────────────────────────────────────────────│
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 4. Field Descriptions

### Simple (Non-Paired) Mode

#### Habitat Lost (Dropdown)
- Select the area habitat being lost/impacted
- Populated from catalog's area habitats
- Includes "Net Gain (10%)" option

#### Habitat to Mitigate (Dropdown)
- Select the area habitat to provide for mitigation
- Populated from catalog's area habitats
- Includes "Net Gain (10%)" option

#### Units (Number Input)
- Number of habitat units required
- Minimum: 0.0
- Step: 0.01

#### Price/Unit (£) (Number Input)
- Price per unit in pounds
- Minimum: 0.0
- Step: 1.0

#### Paired (Checkbox)
- Check to switch to paired mode with full habitat details
- Unchecked = simple mode (single habitat)
- Checked = paired mode (demand + companion habitats)

### Paired Mode (When Checkbox is Ticked)

#### Habitat Lost (Dropdown)
- Same as simple mode - the habitat being impacted

#### Units Required (Number Input)
- Total units of habitat lost that need to be offset
- This is split between demand and companion habitats

#### Demand Habitat Section

**Habitat Type (Dropdown)**
- Primary habitat in the paired allocation
- Selected from area habitats catalog

**Bank (Dropdown)**
- Bank providing the demand habitat
- Populated from available banks in system

**Price/Unit (£) (Number Input)**
- Price per unit for the demand habitat
- Specific to this bank and habitat

#### Companion Habitat Section

**Habitat Type (Dropdown)**
- Secondary/companion habitat in the paired allocation
- Selected from area habitats catalog
- Works together with demand habitat for pairing

**Bank (Dropdown)**
- Bank providing the companion habitat
- Can be same or different from demand bank

**Price/Unit (£) (Number Input)**
- Price per unit for the companion habitat
- Specific to this bank and habitat

#### SRM Tier (Dropdown)
- Strategic Resource Multiplier tier selection
- Options:
  - **local** (SRM = 1.0): Same LPA/NCA
  - **adjacent** (SRM = 1.33): Adjacent LPA/NCA
  - **far** (SRM = 2.0): Far from target site
- Determines how units are calculated for paired allocation

#### Demand Stock Use (Number Input)
- Proportion of total stock from demand habitat
- Range: 0.0 to 1.0
- Default: 0.5 (50/50 split)
- Example: 0.6 means 60% from demand, 40% from companion

#### Companion Stock Use (Metric - Auto-calculated)
- Automatically calculated as 1.0 - Demand Stock Use
- Ensures total equals 100%
- Display only, not editable

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
