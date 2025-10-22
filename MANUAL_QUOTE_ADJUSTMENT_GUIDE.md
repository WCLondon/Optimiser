# Manual Quote Adjustment Feature Guide

## Overview

The Manual Quote Adjustment feature allows users to modify optimization results after the optimizer has completed. This provides the flexibility to customize quotes by removing unwanted allocations and adding manual habitat entries for area, hedgerow, and watercourse habitats.

## Features

### 1. Line Removal Functionality

After optimization completes, each allocation line in the "Allocation detail" section includes a remove button (❌) that allows users to delete specific allocations.

**How it works:**
- Click the ❌ button next to any allocation line to remove it
- Removed lines are immediately excluded from all calculations
- The summary totals update automatically to reflect the removal
- Removed lines are also excluded from the client report

**Use cases:**
- Remove allocations that are geographically undesirable
- Exclude specific habitat banks from the quote
- Simplify quotes by removing less optimal allocations

### 2. Manual Area Habitat Entries

A new section for manual area habitat entries has been added alongside the existing hedgerow and watercourse manual entry sections.

**Fields:**
- **Habitat Lost**: The area habitat being impacted/lost
- **Habitat to Mitigate**: The area habitat being provided for mitigation
- **Units**: Number of habitat units required
- **Price/Unit (£)**: Price per unit in pounds
- **Paired**: Checkbox to indicate if this is a paired habitat allocation

**Paired Toggle:**
When the "Paired" checkbox is selected:
- The system automatically applies the appropriate Strategic Resource Multiplier (SRM)
- For area habitats, a 4/3 SRM multiplier is applied (equivalent to adjacent tier)
- The effective units are calculated as: `units × (4/3)`
- The cost is calculated as: `effective_units × price_per_unit`
- The habitat name is displayed with "(Paired)" suffix in the client report

**Example:**
- Input: 10 units at £100/unit with "Paired" checked
- Calculation: 10 × (4/3) = 13.33 effective units
- Cost: 13.33 × £100 = £1,333.33

### 3. Updated Calculations

All financial summaries automatically update to include:
- Costs from remaining (non-removed) allocation rows
- Costs from manual hedgerow entries
- Costs from manual watercourse entries
- Costs from manual area habitat entries (with SRM applied for paired)

**What gets updated:**
- Optimization Results summary (Subtotal, Admin fee, Grand total)
- Client Report Generation totals
- All habitat breakdowns and summaries

## Usage Workflow

### Step 1: Run Optimization
1. Set up your target location and demand requirements
2. Click "Optimise now"
3. Review the optimization results

### Step 2: Remove Unwanted Lines (Optional)
1. Expand the "📋 Allocation detail" section
2. Review each allocation line
3. Click ❌ next to any lines you want to remove
4. Totals update automatically

### Step 3: Add Manual Entries (Optional)

#### For Area Habitats:
1. Scroll to "➕ Manual Additions (Area, Hedgerow & Watercourse)"
2. Click "➕ Add Area Habitat Entry"
3. Select habitats from dropdowns
4. Enter units and price per unit
5. Check "Paired" if applicable
6. Repeat for additional entries

#### For Hedgerow or Watercourse:
1. Use the respective sections below Area Habitats
2. Follow the same process (without paired option)

### Step 4: Generate Client Report
1. Scroll to "📧 Client Report Generation"
2. Fill in client details (name, reference, location)
3. Click "Generate Report"
4. Review the generated report and email template

## Technical Details

### Session State Variables

New session state variables added:
- `manual_area_rows`: List of manual area habitat entries
- `_next_manual_area_id`: Counter for unique area row IDs
- `removed_allocation_rows`: List of removed allocation row IDs

### SRM Multipliers

The paired functionality applies the following SRM multipliers:
- **Adjacent tier**: 4/3 (≈1.33)
- This matches the standard BNG calculation for paired habitat allocations

### Data Persistence

All manual entries and removed rows persist across:
- Page reruns
- Map interactions
- Report generation
- Until "🔄 Start New Quote" is clicked

## Benefits

1. **Flexibility**: Customize optimization results to meet specific client needs
2. **Control**: Remove allocations that don't meet requirements
3. **Completeness**: Add area habitat manual entries to match hedgerow/watercourse capabilities
4. **Accuracy**: Automatic SRM application ensures correct calculations for paired habitats
5. **Transparency**: All adjustments are reflected in client reports

## Notes

- Manual entries are clearly identified in the client report
- Paired allocations show "(Paired)" suffix in habitat names
- The "🧹 Clear" buttons reset only their respective sections
- "🔄 Start New Quote" clears all data and resets the application
- All changes are reflected in the final totals and client report

## Examples

### Example 1: Remove Expensive Allocations
1. Run optimization
2. Identify high-cost allocations
3. Remove them using ❌ buttons
4. Add manual entries at better prices
5. Generate client report with updated totals

### Example 2: Add Paired Area Habitats
1. Run optimization for basic needs
2. Add manual area habitat entry
3. Check "Paired" option
4. System applies 4/3 SRM automatically
5. Cost calculated with SRM included

### Example 3: Mixed Manual Entries
1. Run optimization
2. Remove 2 allocation lines
3. Add 1 manual area habitat (paired)
4. Add 1 manual hedgerow habitat
5. Add 1 manual watercourse habitat
6. All costs aggregate correctly in client report
