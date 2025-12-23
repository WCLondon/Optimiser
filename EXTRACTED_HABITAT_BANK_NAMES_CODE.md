# Extracted Habitat Bank Names Code for CSV Download

This document contains the exact code from `sales_quotes_csv.py` that builds habitat bank names for the CSV download.

---

## Overview

The habitat bank names for CSV download are built by the `get_standardized_bank_name()` function in `sales_quotes_csv.py`. This function:
1. Looks up the bank in the database using the `BANK_KEY`
2. Retrieves the `bank_id` (e.g., "WC1P2B")
3. Formats the display name as: `first 5 chars of bank_id + " - " + BANK_KEY`

Example outputs:
- "WC1P2 - Nunthorpe"
- "WC1P3 - Cobham"
- "WC1P7 - Fareham"

---

## 1. Bank Name Cache and Database Lookup (lines 19-55)

```python
# Cache for bank names to avoid repeated database queries
_bank_name_cache = None


def get_bank_id_from_database(bank_key: str) -> Optional[str]:
    """
    Get bank_id from the Banks table in the database by looking up BANK_KEY.
    
    Args:
        bank_key: Bank key/name from BANK_KEY column (e.g., "Nunthorpe", "Cobham")
    
    Returns:
        bank_id from database (e.g., "WC1P2B"), or None if not found
    """
    global _bank_name_cache
    
    # Load banks data from database (cached)
    # Cache maps BANK_KEY -> bank_id
    if _bank_name_cache is None:
        try:
            banks_df = fetch_banks()
            if banks_df is not None and not banks_df.empty:
                # Create mapping: BANK_KEY -> bank_id
                _bank_name_cache = {}
                for _, row in banks_df.iterrows():
                    bank_id = row.get('bank_id', '')
                    bank_key_val = row.get('BANK_KEY', '')
                    if bank_key_val and bank_id:
                        _bank_name_cache[str(bank_key_val).strip()] = str(bank_id).strip()
            else:
                _bank_name_cache = {}
        except Exception:
            # Database not available (e.g., in tests) - use empty cache
            _bank_name_cache = {}
    
    # Look up bank_id by BANK_KEY
    return _bank_name_cache.get(bank_key.strip())
```

**How it works:**
1. First call loads all banks from database via `fetch_banks()` (from `repo.py`)
2. Creates a cache mapping `BANK_KEY` → `bank_id`
3. Subsequent calls use the cached mapping
4. Returns `bank_id` (e.g., "WC1P2B") or `None` if not found

---

## 2. Valid Bank Combinations Reference (lines 58-71)

```python
# Bank reference to bank name mapping - Updated list from user
# Format: first 5 chars of bank_id + " - " + bank_name
VALID_BANK_COMBINATIONS = [
    ("WC1P6", "Central Bedfordshire"),
    ("WC1P4", "Barnsley"),
    ("WC1P6", "Denchworth"),
    ("WC1P2", "Horden"),
    ("WC1P2", "Stokesley"),
    ("WC1P5", "Bedford"),
    ("WC1P8", "Marbury"),
    ("WC1P2", "Nunthorpe"),
    ("WC1P7", "Fareham"),
    ("WC1P3", "Cobham"),
]
```

**Note:** This is a reference list. The actual bank names are now dynamically looked up from the database.

---

## 3. THE MAIN FUNCTION: `get_standardized_bank_name()` (lines 74-103)

This is the core function that builds the habitat bank name for CSV:

```python
def get_standardized_bank_name(bank_key: str, bank_name: str) -> Tuple[str, str, str]:
    """
    Get standardized bank name format from Banks table in database.
    Uses format: first 5 chars of bank_id + " - " + BANK_KEY
    
    Args:
        bank_key: Bank reference from BANK_KEY column (e.g., "Nunthorpe", "Cobham")
        bank_name: Bank name (same as bank_key in most cases)
    
    Returns:
        Tuple of (standardized_bank_name, notes_for_column_S, source_display)
        - standardized_bank_name: Bank name from database or 'Other'
        - notes_for_column_S: Empty string or the actual bank name if using 'Other'
        - source_display: The full "ref - name" string for column AC
    """
    bank_key = bank_key.strip()
    bank_name = bank_name.strip()
    
    # Get bank_id from database by looking up the BANK_KEY
    bank_id = get_bank_id_from_database(bank_key)
    
    if bank_id:
        # Found in database - use first 5 chars of bank_id
        bank_id_short = bank_id[:5] if len(bank_id) >= 5 else bank_id
        return bank_key, "", f"{bank_id_short} - {bank_key}"
    else:
        # Not found in database - use 'Other' and put actual name in notes
        # Try to extract first 5 chars from bank_key
        bank_key_short = bank_key[:5] if len(bank_key) >= 5 else bank_key
        return "Other", bank_key, f"{bank_key_short} - Other"
```

**Return values:**
1. `standardized_bank_name` - The bank name to use (e.g., "Nunthorpe" or "Other")
2. `notes_for_column_S` - Notes if bank not found (empty string if found)
3. `source_display` - The formatted string for CSV column AC: `"WC1P2 - Nunthorpe"`

---

## 4. Usage in CSV Generation (lines 243-244, 321-322)

The function is called when building each CSV row:

```python
# Get standardized bank name and check if we need to use 'Other'
standardized_bank_name, bank_fallback_note, source_display = get_standardized_bank_name(bank_ref, bank_name)

# ...

# Column AC (index 28): Habitat Bank / Source of Mitigation
# Use the standardized display format (first 5 chars + " - " + name)
row[28] = source_display
```

---

## 5. Where Bank Key/Name Come From

In `generate_sales_quotes_csv_from_optimizer_output()`, the bank key and name are extracted from the allocation DataFrame:

```python
# Group by bank
for bank_key, bank_group in alloc_df.groupby(bank_ref_col):
    bank_name = bank_group["bank_name"].iloc[0] if "bank_name" in bank_group.columns else str(bank_key)
    
    # ... later in the function ...
    
    allocations.append({
        "bank_ref": str(bank_key),    # BANK_KEY from allocation
        "bank_name": bank_name,        # bank_name from allocation
        # ...
    })
```

---

## Complete Call Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    OPTIMIZATION COMPLETES                                │
│  alloc_df contains BANK_KEY and bank_name columns                        │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│         generate_sales_quotes_csv_from_optimizer_output()                │
│  Groups allocations by bank (BANK_KEY)                                   │
│  Extracts bank_name from allocation data                                 │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    generate_sales_quotes_csv()                           │
│  For each allocation:                                                    │
│    1. Call get_standardized_bank_name(bank_ref, bank_name)               │
│    2. Returns (standardized_name, notes, source_display)                 │
│    3. Put source_display in CSV column AC (index 28)                     │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    get_standardized_bank_name()                          │
│  1. Lookup BANK_KEY in database via get_bank_id_from_database()          │
│  2. If found: bank_id_short = bank_id[:5]                                │
│     Return (bank_key, "", f"{bank_id_short} - {bank_key}")               │
│  3. If not found:                                                        │
│     Return ("Other", bank_key, f"{bank_key[:5]} - Other")                │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    get_bank_id_from_database()                           │
│  1. First call: fetch_banks() from database, cache results               │
│  2. Cache maps: BANK_KEY → bank_id                                       │
│  3. Return bank_id (e.g., "WC1P2B") or None                              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Example Output

| Input (BANK_KEY) | Database bank_id | CSV Column AC Output |
|------------------|------------------|----------------------|
| Nunthorpe        | WC1P2B           | WC1P2 - Nunthorpe    |
| Cobham           | WC1P3A           | WC1P3 - Cobham       |
| Fareham          | WC1P7C           | WC1P7 - Fareham      |
| Unknown Bank     | (not found)      | Unkno - Other        |

---

## Summary

The habitat bank name for CSV is built by:
1. Looking up `BANK_KEY` in the database to get `bank_id`
2. Taking first 5 characters of `bank_id`
3. Formatting as: `"{bank_id[:5]} - {BANK_KEY}"`
4. Placing result in CSV column AC (index 28) - "Habitat Bank / Source of Mitigation"

If the bank is not found in the database, it returns "Other" with the actual bank name in the notes column.
