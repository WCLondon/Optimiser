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

The importer extracts **deficits only** (negative project-wide unit changes) from:

- **Trading Summary Area Habitats** sheet
- **Trading Summary Hedgerows** sheet  
- **Trading Summary Watercourses** sheet

All extracted deficits are converted to positive values (absolute values) representing units required.

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
   → Parser extracts:
     - Grassland (Medium distinctiveness): 5.23 units
     - Woodland (High distinctiveness): 3.45 units
     - Hedgerow: 2.10 units

2. Click "Add to Demand Rows"
   → Demand table populated with 3 rows

3. Proceed with optimization as normal
   → Optimizer finds best allocation across banks
```

## Troubleshooting

**Q: File upload fails with "Could not open workbook"**
A: Try re-saving the file as .xlsx format in Excel

**Q: No requirements found in preview**
A: Ensure your file has Trading Summary sheets with negative project-wide unit changes

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
