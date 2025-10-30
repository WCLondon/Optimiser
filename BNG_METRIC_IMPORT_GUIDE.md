# BNG Metric Import Feature

## Overview

The BNG Optimiser now supports importing requirements directly from DEFRA BNG metric files (.xlsx, .xlsm, or .xlsb). This feature automatically extracts habitat deficits from Trading Summary sheets and populates the demand table, eliminating manual data entry.

## How to Use

1. **Navigate to the Demand section** (Section 2 in the app)

2. **Expand "📄 Import from BNG Metric File"** expander

3. **Upload your metric file**:
   - Click "Browse files" or drag and drop
   - Supported formats: .xlsx, .xlsm, .xlsb
   - File must contain Trading Summary sheets

4. **Review the preview**:
   - Area Habitats: Shows area habitat deficits
   - Hedgerows: Shows hedgerow deficits  
   - Watercourses: Shows watercourse deficits

5. **Import to demand table**:
   - Click "➕ Add to Demand Rows"
   - If you have existing entries, click "Clear & Import" to confirm
   - The demand table will be populated automatically

## What Gets Imported

The importer follows the **exact logic of the DEFRA BNG Metric Reader app** to calculate off-site mitigation requirements:

### Area Habitats (Full Trading Logic)
1. **On-site offsets applied**: Surpluses offset deficits according to habitat trading rules
2. **Headline Net Gain calculated**: Target % × baseline units from Headline Results sheet
3. **Surpluses allocated to headline**: Remaining surpluses reduce headline requirement
4. **Residual extracted**: Only what needs OFF-SITE mitigation:
   - Habitat deficits after on-site offsets
   - Headline Net Gain remainder after surplus allocation

This matches the "🧮 Still needs mitigation OFF-SITE" total from the metric reader.

### Hedgerows & Watercourses (Simple Deficits)
- Extracts raw deficits (negative project-wide unit changes)
- No trading rules applied (per DEFRA guidance)
- All values converted to positive units required

**Key Point**: You get the **combined off-site mitigation total**, not raw deficits. The metric reader's trading rules and headline logic are applied automatically.

## Habitat Matching

The importer attempts to match extracted habitat names to the optimizer's habitat catalog:

- **Exact matches**: Used as-is
- **Area habitats not in catalog**: Kept as original name
- **Hedgerows not in catalog**: Mapped to "Net Gain (Hedgerows)"
- **Watercourses not in catalog**: Mapped to "Net Gain (Watercourses)"

## Technical Details

### Supported Sheet Names

The parser looks for sheets with these names (case-insensitive):

**Area Habitats:**
- Trading Summary Area Habitats
- Area Habitats Trading Summary
- Area Trading Summary
- Trading Summary (Area Habitats)

**Hedgerows:**
- Trading Summary Hedgerows
- Hedgerows Trading Summary
- Hedgerow Trading Summary
- Trading Summary (Hedgerows)

**Watercourses:**
- Trading Summary WaterCs
- Trading Summary Watercourses
- Watercourses Trading Summary
- Trading Summary (Watercourses)

### Required Columns

The parser expects these columns in Trading Summary sheets:
- **Habitat** (or Feature): Habitat name
- **Project-wide unit change** (or Project wide unit change): Deficit/surplus values
- **On-site unit change** (optional): On-site changes
- **Habitat group** (optional): Broad habitat group
- **Distinctiveness** (derived from sheet headers): Very High, High, Medium, or Low

### Error Handling

- Invalid or corrupted files: Clear error message displayed
- Missing sheets: Silently skipped (returns empty DataFrame)
- Invalid data: Safe float conversion with fallback to 0.0
- Non-numeric units: Filtered out during import

## Files Added/Modified

### New Files
- `metric_reader.py`: Core parsing module
- `test_metric_reader.py`: Unit tests for metric reader

### Modified Files
- `app.py`: Added file uploader UI and integration
- `requirements.txt`: Added openpyxl and pyxlsb dependencies

## Backward Compatibility

This feature is **fully backward compatible**:
- Existing manual entry workflow unchanged
- No breaking changes to existing functionality
- New dependencies are widely used and stable

## Example Workflow

```
1. Upload "Project_BNG_Metric_v4.0.xlsx"
   → Metric reader logic applied:
     a) On-site offsets: Surpluses reduce deficits via trading rules
     b) Headline Net Gain: 10% × 100 baseline = 10.0 units target
     c) Surplus allocation: 3.5 units surplus → covers part of headline
     d) Residual calculated:
        - Grassland (after offsets): 2.8 units
        - Headline Net Gain (after surplus): 6.5 units
        - Hedgerow deficit: 2.10 units
   → Parser extracts OFF-SITE requirements only:
     - Grassland: 2.8 units
     - Headline Net Gain (10%): 6.5 units  
     - Hedgerow: 2.10 units

2. Click "Add to Demand Rows"
   → Demand table populated with 3 rows

3. Proceed with optimization as normal
   → Optimizer finds best allocation across banks for off-site mitigation
```

## Troubleshooting

**Q: File upload fails with "Could not open workbook"**
A: Try re-saving the file as .xlsx format in Excel

**Q: No requirements found in preview**
A: Check that your file has:
   - Trading Summary sheets with project-wide unit changes
   - Headline Results sheet (for area habitats)
   - Actual deficits after on-site offsets and surplus allocation

**Q: Numbers don't match raw deficits in metric**
A: This is correct! The importer applies trading rules and headline logic, just like the metric reader app. You're seeing off-site mitigation needs, not raw deficits.

**Q: Habitat names don't match catalog**
A: Generic Net Gain labels will be used automatically. You can manually edit after import.

**Q: Import button does nothing**
A: Check browser console for errors. Ensure you clicked "Clear & Import" if you have existing rows.

## Future Enhancements

Potential improvements for future versions:
- Support for more metric file formats
- Smart habitat name matching with fuzzy search
- Import of surplus units as supply
- Parsing of headline requirements
- Export of optimization results back to metric format
