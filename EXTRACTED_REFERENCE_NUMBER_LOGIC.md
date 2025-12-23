# Extracted Reference Number Logic for Quotes

This document explains the reference number system used for quotes, including:
1. **New quote numbering** - Sequential BNG-A-XXXXX format
2. **Multipart quote suffixes** - Appending a, b, c, etc. for multi-bank allocations
3. **Requote/revision suffixes** - Appending .1, .2, etc. for requotes of the same project

---

## Overview: Reference Number Formats

| Type | Format | Example |
|------|--------|---------|
| New Quote | `BNG-A-XXXXX` | `BNG-A-02025` |
| Multipart Quote | `BNG-A-XXXXXa`, `BNG-A-XXXXXb` | `BNG-A-02025a`, `BNG-A-02025b` |
| Requote | `BNG-A-XXXXX.1`, `BNG-A-XXXXX.2` | `BNG-A-02025.1`, `BNG-A-02025.2` |
| Multipart Requote | `BNG-A-XXXXX.1a`, `BNG-A-XXXXX.1b` | `BNG-A-02025.1a`, `BNG-A-02025.1b` |

---

## 1. New Quote Numbering (database.py, lines 1708-1748)

When a new quote is created, the system generates the next sequential reference number:

```python
def get_next_bng_reference(self, prefix: str = "BNG-A-") -> str:
    """
    Generate the next sequential BNG reference number.
    
    Args:
        prefix: Reference number prefix (default: "BNG-A-")
    
    Returns:
        Next reference number in format "BNG-A-XXXXX" (e.g., "BNG-A-02025")
    
    Example:
        If latest reference is "BNG-A-02025", returns "BNG-A-02026"
        If no references exist, returns "BNG-A-02025" (starting number)
    """
    engine = self._get_connection()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT reference_number FROM submissions
            WHERE reference_number LIKE :pattern
            ORDER BY reference_number DESC
            LIMIT 1
        """), {"pattern": f"{prefix}%"})
        
        row = result.fetchone()
        
        if not row:
            # No existing references with this prefix, start at 02025
            return f"{prefix}02025"
        
        # Extract the numeric part from the latest reference
        latest_ref = row[0]
        try:
            # Remove prefix to get numeric part (e.g., "BNG-A-02025" -> "02025")
            numeric_part = latest_ref.replace(prefix, "").split('.')[0]  # Remove any revision suffix
            next_number = int(numeric_part) + 1
            # Format with same number of digits (5 digits with leading zeros)
            return f"{prefix}{next_number:05d}"
        except (ValueError, IndexError):
            # If parsing fails, start at 02025
            return f"{prefix}02025"
```

### How It Works:
1. Query database for the highest reference number with prefix `BNG-A-`
2. If no references exist, start at `BNG-A-02025`
3. If references exist, extract the numeric part (ignoring any `.X` revision suffix)
4. Increment by 1 and format with 5 digits (zero-padded)
5. Return the new reference: e.g., `BNG-A-02026`

---

## 2. Multipart Quote Suffixes - a, b, c (sales_quotes_csv.py, lines 291-296)

When a quote has allocations from **multiple banks**, each bank gets its own CSV row with a letter suffix:

```python
# Column D (index 3): Ref
# If multiple allocations, suffix with letters (a, b, c, ...)
if num_allocations > 1:
    suffix = chr(ord('a') + alloc_idx)  # a, b, c, ...
    row[3] = f"{base_ref}{suffix}"
else:
    row[3] = base_ref
```

### How It Works:
1. Check if there are multiple allocations (allocations from different banks)
2. If multiple: append a letter suffix using `chr(ord('a') + index)`
   - Index 0 → 'a'
   - Index 1 → 'b'
   - Index 2 → 'c'
   - etc.
3. If single allocation: use the base reference as-is

### Example:
A quote `BNG-A-02025` with allocations from 3 banks generates:
- Row 1: `BNG-A-02025a` (Bank A allocation)
- Row 2: `BNG-A-02025b` (Bank B allocation)
- Row 3: `BNG-A-02025c` (Bank C allocation)

---

## 3. Requote/Revision Suffixes - .1, .2 (database.py, lines 1671-1706)

When creating a requote (revised quote for the same project), the system appends a revision number:

```python
def get_next_revision_number(self, base_reference: str) -> str:
    """
    Get the next revision number for a reference.
    E.g., for BNG01234, returns BNG01234.1 if no revisions exist,
    or BNG01234.2 if BNG01234.1 exists, etc.
    """
    engine = self._get_connection()
    
    # Strip any existing revision suffix
    base_ref = base_reference.split('.')[0]
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT reference_number FROM submissions
            WHERE reference_number LIKE :pattern
            ORDER BY reference_number DESC
        """), {"pattern": f"{base_ref}%"})
        
        rows = result.fetchall()
        
        if not rows:
            # No existing references, return base.1
            return f"{base_ref}.1"
        
        # Find the highest revision number
        max_revision = 0
        for row in rows:
            ref = row[0]
            if '.' in ref:
                try:
                    revision = int(ref.split('.')[-1])
                    max_revision = max(max_revision, revision)
                except ValueError:
                    pass
        
        return f"{base_ref}.{max_revision + 1}"
```

### How It Works:
1. Strip any existing revision suffix from the input reference (e.g., `BNG-A-02025.1` → `BNG-A-02025`)
2. Query database for all references matching the base pattern
3. If no references exist, return `{base_ref}.1`
4. If references exist, find the highest revision number:
   - Parse each reference for a `.X` suffix
   - Track the maximum revision number found
5. Return `{base_ref}.{max_revision + 1}`

### Example:
```
Original quote:     BNG-A-02025
First requote:      BNG-A-02025.1
Second requote:     BNG-A-02025.2
Third requote:      BNG-A-02025.3
```

---

## 4. Combined Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         NEW QUOTE CREATED                                │
│  User submits a new quote → get_next_bng_reference() is called          │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    GENERATE SEQUENTIAL NUMBER                            │
│  1. Query: SELECT MAX(reference_number) WHERE LIKE 'BNG-A-%'            │
│  2. Extract numeric part: "BNG-A-02025" → 02025                         │
│  3. Increment: 02025 → 02026                                            │
│  4. Format: "BNG-A-02026"                                               │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌───────────────────────────────┐   ┌───────────────────────────────────┐
│    SINGLE BANK ALLOCATION     │   │     MULTI-BANK ALLOCATION         │
│                               │   │                                   │
│  Reference: BNG-A-02026       │   │  Reference + letter suffix:       │
│  (no suffix needed)           │   │    Bank 1: BNG-A-02026a           │
│                               │   │    Bank 2: BNG-A-02026b           │
│                               │   │    Bank 3: BNG-A-02026c           │
└───────────────────────────────┘   └───────────────────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         REQUOTE REQUESTED                                │
│  User selects original quote → get_next_revision_number() is called     │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    GENERATE REVISION NUMBER                              │
│  1. Strip existing revision: "BNG-A-02026.1" → "BNG-A-02026"            │
│  2. Query: SELECT all WHERE reference_number LIKE 'BNG-A-02026%'        │
│  3. Find max revision: .1, .2 → max = 2                                 │
│  4. Increment: 2 → 3                                                    │
│  5. Return: "BNG-A-02026.3"                                             │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌───────────────────────────────┐   ┌───────────────────────────────────┐
│    SINGLE BANK REQUOTE        │   │     MULTI-BANK REQUOTE            │
│                               │   │                                   │
│  Reference: BNG-A-02026.3     │   │  Reference + letter suffix:       │
│  (no letter suffix needed)    │   │    Bank 1: BNG-A-02026.3a         │
│                               │   │    Bank 2: BNG-A-02026.3b         │
└───────────────────────────────┘   └───────────────────────────────────┘
```

---

## 5. Reference Number Examples

### Scenario 1: Simple New Quote
```
User creates new quote → BNG-A-02026
Only 1 bank allocation → BNG-A-02026 (no suffix)
```

### Scenario 2: Multi-Bank New Quote
```
User creates new quote → BNG-A-02027
3 bank allocations:
  - Bank Nunthorpe → BNG-A-02027a
  - Bank Cobham    → BNG-A-02027b
  - Bank Fareham   → BNG-A-02027c
```

### Scenario 3: Requote of Simple Quote
```
Original quote: BNG-A-02025 (single bank)
First requote:  BNG-A-02025.1 (single bank)
Second requote: BNG-A-02025.2 (single bank)
```

### Scenario 4: Requote of Multi-Bank Quote
```
Original quote: BNG-A-02028a, BNG-A-02028b (2 banks)
First requote:  BNG-A-02028.1a, BNG-A-02028.1b (2 banks)
Second requote: BNG-A-02028.2a, BNG-A-02028.2b (2 banks)
```

### Scenario 5: Multi-Bank Requote with Different Bank Count
```
Original quote: BNG-A-02029a, BNG-A-02029b (2 banks)
First requote:  BNG-A-02029.1a, BNG-A-02029.1b, BNG-A-02029.1c (3 banks - added one)
Second requote: BNG-A-02029.2a (1 bank - consolidated to single bank)
```

---

## 6. Key Database Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `get_next_bng_reference()` | database.py:1708 | Generate next sequential quote number |
| `get_next_revision_number()` | database.py:1671 | Generate next .X revision for requotes |
| `create_requote_from_submission()` | database.py:1763 | Copy submission with new revision number |
| `get_quotes_by_reference_base()` | database.py:1750 | Get all quotes with same base reference |

---

## 7. Important Notes for Copilot

### When to Use Each Suffix Type:

1. **Letter suffixes (a, b, c)**: 
   - Applied in **CSV generation** (`sales_quotes_csv.py`)
   - Only when quote has **multiple bank allocations**
   - Each bank's allocation row gets its own letter

2. **Revision suffixes (.1, .2)**:
   - Applied in **database layer** (`database.py`)
   - When user clicks **"Create Requote"** button
   - Keeps original reference but adds revision number

### Order of Application:
```
Base Number → Revision Suffix → Letter Suffix
BNG-A-02025 → BNG-A-02025.1 → BNG-A-02025.1a
```

### Parsing Logic:
- To get base reference: `reference.split('.')[0]`
- To get revision number: `reference.split('.')[-1]` (if contains '.')
- Letter suffix is always at the very end (after revision if present)
