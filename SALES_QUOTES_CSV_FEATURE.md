# Sales & Quotes CSV Export Feature

## Overview

This feature generates CSV data rows (no headers) for the Sales & Quotes Excel workbook after the optimizer runs. The CSV output can be directly pasted into Excel, with proper column alignment and formatting.

## Features

### Core Functionality

- **One allocation = one row**: Each bank allocation generates a separate CSV row
- **Multi-bank ref suffixing**: For quotes split across multiple banks, references are suffixed with letters (a, b, c...)
- **103 columns (A-CY)**: Full column mapping to match Excel workbook structure
- **Up to 8 habitats**: Each allocation can include up to 8 different habitat types
- **Proper CSV escaping**: Fields with commas, quotes, or newlines are properly escaped
- **Date formatting**: Dates formatted as DD/MM/YYYY for Excel compatibility

### Column Mapping

| Column | Index | Field | Description |
|--------|-------|-------|-------------|
| A | 0 | (blank) | Intentionally left blank |
| B | 1 | Client | Client name |
| C | 2 | Address | Development address |
| D | 3 | Ref | Reference number (with a,b,c suffix for multi-allocations) |
| E-S | 4-18 | (blank) | Intentionally left blank |
| T | 19 | Notes | SRM notes for paired allocations |
| U-AB | 20-27 | (blank) | Intentionally left blank |
| AC | 28 | Habitat Bank | Bank reference - Bank name |
| AD | 29 | Spatial Multiplier | Formula (=4/3, =2/1) or numeric 1 |
| AE-AG | 30-32 | (blank) | Intentionally left blank |
| AH | 33 | LPA | Local Planning Authority |
| AI | 34 | NCA | National Character Area |
| AJ | 35 | (blank) | Intentionally left blank |
| AK | 36 | Introducer | Introducer name or "Direct" |
| AL | 37 | Quote Date | Date in DD/MM/YYYY format |
| AM-AQ | 38-42 | (blank) | Intentionally left blank |
| AR | 43 | Admin Fee | £500 (£300 for fractional) |
| AS-AU | 44-46 | (blank) | Intentionally left blank |
| AV-CY | 47-102 | Habitats 1-8 | 8 habitat sections, 7 columns each |

### Habitat Section Structure

Each habitat occupies 7 columns with the following structure:
1. **Type**: Habitat type name
2. **# credits**: Number of units (uses `effective_units` for paired, `units_supplied` for non-paired)
3. **ST**: (blank - managed by Excel)
4. **Standard Price**: (blank - managed by Excel)
5. **Quoted Price**: Average effective unit price
6. **Minimum**: (blank - managed by Excel)
7. **Price inc SM**: (blank - managed by Excel)

### SRM and Spatial Multiplier Logic

The feature implements different logic based on whether the allocation is paired or non-paired:

#### Paired Allocations (`is_paired = true`)

- **Column T (Notes)**:
  - `spatial_relation = "far"` → `"SRM manual (0.5)"`
  - `spatial_relation = "adjacent"` → `"SRM manual (0.75)"`
  
- **Column AD (Spatial Multiplier)**: Always numeric `1`

- **Habitat # credits**: Uses `effective_units`

#### Non-Paired Allocations (`is_paired = false`)

- **Column T (Notes)**: Blank

- **Column AD (Spatial Multiplier)**:
  - `spatial_relation = "adjacent"` → Formula `"=4/3"`
  - `spatial_relation = "far"` → Formula `"=2/1"`
  - Otherwise → `"1"`

- **Habitat # credits**: Uses `units_supplied`

## Usage

### From the Streamlit App

1. Run the optimizer to generate allocation results
2. Navigate to the "Client Report Generation" section
3. Fill in the client details (name, reference, location)
4. Click "Generate Report" to generate the email
5. Click "📥 Download Sales & Quotes CSV" button
6. Save the CSV file
7. Open the Sales & Quotes Excel workbook
8. Paste the CSV data into the appropriate location

### Programmatic Usage

#### Method 1: Direct Function

```python
from datetime import datetime
from sales_quotes_csv import generate_sales_quotes_csv

# Define allocations
allocations = [{
    "bank_ref": "WC1P2",
    "bank_name": "Nunthorpe",
    "is_paired": False,
    "spatial_relation": "adjacent",
    "spatial_multiplier_numeric": 4.0/3.0,
    "allocation_total_credits": 10.0,
    "contract_value_gbp": 10000.0,
    "habitats": [{
        "type": "Grassland - Other neutral grassland",
        "units_supplied": 10.0,
        "effective_units": 13.33,
        "avg_effective_unit_price": 750.0
    }]
}]

# Generate CSV
csv_output = generate_sales_quotes_csv(
    quote_number="1923",
    client_name="David Evans",
    development_address="123 High Street, London",
    base_ref="BNG01640",
    introducer="John Smith",
    today_date=datetime.now(),
    local_planning_authority="Westminster",
    national_character_area="Thames Valley",
    allocations=allocations,
    contract_size="small"
)

# Save to file
with open("sales_quotes.csv", "w") as f:
    f.write(csv_output)
```

#### Method 2: From Optimizer DataFrame

```python
from datetime import datetime
import pandas as pd
from sales_quotes_csv import generate_sales_quotes_csv_from_optimizer_output

# Get allocation DataFrame from optimizer
alloc_df = pd.DataFrame([
    {
        "BANK_KEY": "WC1P2",
        "bank_name": "Nunthorpe",
        "allocation_type": "normal",
        "tier": "adjacent",
        "supply_habitat": "Grassland - Other neutral grassland",
        "units_supplied": 10.0,
        "unit_price": 1000.0,
        "cost": 10000.0
    }
])

# Generate CSV
csv_output = generate_sales_quotes_csv_from_optimizer_output(
    quote_number="1923",
    client_name="David Evans",
    development_address="123 High Street",
    base_ref="BNG01640",
    introducer="John Smith",
    today_date=datetime.now(),
    local_planning_authority="Westminster",
    national_character_area="Thames Valley",
    alloc_df=alloc_df,
    contract_size="small"
)
```

## Examples

### Example 1: Single Allocation

**Input:**
- 1 allocation (non-paired, adjacent tier)
- 1 habitat: Grassland (10 units)

**Output:**
```csv
,David Evans,"123 High Street, London",BNG01640,,,,,,,,,,,,,,,,,,,,,,,,,WC1P2 - Nunthorpe,=4/3,,,,Westminster,Thames Valley,,John Smith,10/11/2025,,,,,,500.0,,,,Grassland - Other neutral grassland,10.0,,,1125.0,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
```

**Key Fields:**
- Column B: David Evans
- Column D: BNG01640 (no suffix)
- Column T: (blank)
- Column AD: =4/3
- Column AV: Grassland - Other neutral grassland
- Column AW: 10.0

### Example 2: Multi-Bank Allocation

**Input:**
- 2 allocations (same quote, different banks)

**Output:**
```csv
,Jane Doe,"456 Street, Cambridge",BNG01641a,...
,Jane Doe,"456 Street, Cambridge",BNG01641b,...
```

**Key Feature:** Refs are BNG01641a and BNG01641b

### Example 3: Paired Allocation

**Input:**
- 1 allocation (paired, far tier)

**Output:**
```csv
,Client,"Address",BNG01642,,,,,,,,,,,,,,,,SRM manual (0.5),,,,,,,,,Bank - Name,1,...
```

**Key Fields:**
- Column T: SRM manual (0.5)
- Column AD: 1 (numeric)

## Testing

The feature includes comprehensive test coverage:

```bash
# Run all tests
pytest test_sales_quotes_csv.py -v

# Run specific test
pytest test_sales_quotes_csv.py::test_single_allocation_basic -v
```

**Test Coverage:**
- Admin fee calculation (fractional vs standard)
- Single allocation basic case
- Multi-allocation ref suffixing
- Paired allocation SRM notes
- Non-paired spatial multiplier formulas
- Habitat units (paired vs non-paired)
- CSV escaping (commas, quotes)
- DataFrame conversion
- Empty DataFrame handling
- Date formatting
- Multiple habitats (up to 8)
- Habitat limit enforcement

All 13 tests pass successfully.

## Demo

Run the demo script to see example outputs:

```bash
python demo_csv_generation.py
```

This will show:
1. Single allocation (non-paired, adjacent)
2. Multi-bank allocations with ref suffixing
3. Paired allocation with SRM notes
4. Multiple habitats in one allocation
5. DataFrame conversion

## Security

- ✅ No SQL injection vulnerabilities
- ✅ No code execution vulnerabilities
- ✅ Proper CSV escaping for user input
- ✅ No hardcoded credentials
- ✅ CodeQL security scan: 0 alerts

## Limitations

- Maximum 8 habitats per allocation (as per Excel workbook design)
- CSV output does not include headers (by design)
- Assumes Excel workbook column structure from A-CY (103 columns)
- Only fills specific columns; many are intentionally left blank for Excel formulas

## Files

- **`sales_quotes_csv.py`** - Core CSV generation module
- **`test_sales_quotes_csv.py`** - Test suite
- **`demo_csv_generation.py`** - Demo script with examples
- **`app.py`** - Streamlit integration (download button)

## Dependencies

- `pandas` - DataFrame handling
- `datetime` - Date formatting
- `optimizer_core` - Admin fee constants

## Future Enhancements

Potential improvements for future versions:

- [ ] Support for more than 8 habitats (if Excel workbook is expanded)
- [ ] Include header row option
- [ ] Support for different Excel workbook templates
- [ ] Batch processing for multiple quotes
- [ ] CSV validation against Excel workbook schema
- [ ] Direct Excel file generation (instead of CSV)

## Troubleshooting

### Issue: Fields with commas are not parsed correctly

**Solution:** The CSV uses proper escaping. Use a CSV parser (like Python's `csv` module or Excel's import) instead of simple string splitting.

### Issue: Date format is incorrect

**Solution:** Ensure the `today_date` parameter is a `datetime` object. The module will format it as DD/MM/YYYY automatically.

### Issue: Spatial multiplier shows as text instead of formula

**Solution:** This is expected. Excel will interpret strings starting with `=` as formulas when pasted.

### Issue: Too many habitats

**Solution:** The module limits output to 8 habitats. If you have more, only the first 8 will be included. This matches the Excel workbook design.

## Support

For issues or questions:
1. Check the test cases in `test_sales_quotes_csv.py` for examples
2. Run the demo script: `python demo_csv_generation.py`
3. Review the module docstrings for detailed parameter information
4. Check the issue tracker on GitHub
