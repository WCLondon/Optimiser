# Extracted Client Report Table, Email Generation, and CSV Allocation Code

This document contains the exact code from `app.py` and `sales_quotes_csv.py` that handles the client report table, email generation, and CSV allocation after optimization.

---

## Overview: Client Report Generation Flow

After optimization completes, the system generates:
1. **Client Report Table** - A formatted HTML table showing habitat allocations, costs, and totals
2. **Email (.eml file)** - A complete client-facing email with the report table embedded
3. **Sales & Quotes CSV** - CSV data formatted for the Sales & Quotes Excel workbook

### Flow Summary

1. **Optimization completes** → Results stored in `st.session_state["last_alloc_df"]`
2. **User enters client details** → Client name, location, customer info in form
3. **Click "Update Email Details"** → Triggers `generate_client_report_table_fixed()`
4. **Report Table is displayed** → Shows allocation breakdown with prices
5. **Download options available** → Email (.eml) and CSV exports

---

## 1. Session State Variables (app.py, lines 6114-6119)

```python
# Initialize email inputs in session state (only if not exists)
if "email_client_name" not in st.session_state:
    st.session_state.email_client_name = "INSERT NAME"
if "email_location" not in st.session_state:
    st.session_state.email_location = "INSERT LOCATION"
# Auto-generated reference - removed from session state initialization
```

---

## 2. Entry Point - Check for Results (app.py, lines 6072-6082)

```python
# Allow client report generation if optimization was run OR if there are manual entries
has_optimizer_results = (st.session_state.get("optimization_complete", False) and 
                         isinstance(st.session_state.get("last_alloc_df"), pd.DataFrame) and 
                         not st.session_state["last_alloc_df"].empty)

has_manual_entries = (st.session_state.get("optimization_complete", False) and
                     (len(st.session_state.get("manual_hedgerow_rows", [])) > 0 or
                      len(st.session_state.get("manual_watercourse_rows", [])) > 0 or
                      len(st.session_state.get("manual_area_rows", [])) > 0))

if has_optimizer_results or has_manual_entries:
    # ... report generation code ...
```

---

## 3. THE MAIN FUNCTION: `generate_client_report_table_fixed()` (app.py, lines 4649-5437)

This is the core function that generates the client report table and email HTML:

```python
def generate_client_report_table_fixed(alloc_df: pd.DataFrame, demand_df: pd.DataFrame, total_cost: float, admin_fee: float, 
                                       client_name: str, ref_number: str, location: str,
                                       manual_hedgerow_rows: List[dict] = None,
                                       manual_watercourse_rows: List[dict] = None,
                                       manual_area_rows: List[dict] = None,
                                       removed_allocation_rows: List[int] = None,
                                       promoter_name: str = None,
                                       promoter_discount_type: str = None,
                                       promoter_discount_value: float = None,
                                       suo_discount_fraction: float = 0.0) -> Tuple[pd.DataFrame, str]:
    """Generate the client-facing report table and email body matching exact template with improved styling"""
    
    if manual_hedgerow_rows is None:
        manual_hedgerow_rows = []
    if manual_watercourse_rows is None:
        manual_watercourse_rows = []
    if manual_area_rows is None:
        manual_area_rows = []
    if removed_allocation_rows is None:
        removed_allocation_rows = []
    
    # Helper function to round unit price to nearest £50
    def round_to_50(price):
        return round(price / 50) * 50
    
    # Helper function to format units with up to 3 decimal places (4 sig figs)
    def format_units_dynamic(value):
        """Format units to show up to 3 decimal places."""
        if value == 0:
            return "0.00"
        formatted = f"{value:.3f}"
        parts = formatted.split('.')
        if len(parts) == 2:
            integer_part = parts[0]
            decimal_part = parts[1].rstrip('0')
            if len(decimal_part) < 2:
                decimal_part = decimal_part.ljust(2, '0')
            return f"{integer_part}.{decimal_part}"
        return formatted
    
    # Filter out removed allocation rows
    if "_row_id" not in alloc_df.columns:
        alloc_df = alloc_df.copy()
        alloc_df["_row_id"] = range(len(alloc_df))
    alloc_df = alloc_df[~alloc_df["_row_id"].isin(removed_allocation_rows)]
    
    # Separate by habitat types
    area_habitats = []
    hedgerow_habitats = []
    watercourse_habitats = []
    
    # Process each demand and matching allocation...
    # [Full implementation in app.py lines 4729-4856]
    
    # Process manual entries...
    # [Full implementation in app.py lines 4857-5129]
    
    # Calculate total cost from line items
    total_cost_with_manual = 0.0
    for habitat_list in [area_habitats, hedgerow_habitats, watercourse_habitats]:
        for row in habitat_list:
            cost_str = row["Offset Cost"].replace("£", "").replace(",", "")
            total_cost_with_manual += float(cost_str)
    
    total_with_admin = total_cost_with_manual + admin_fee
    
    # Bundle Low + 10% Net Gain rows together
    # [Implementation in app.py lines 5144-5206]
    
    # Sort by distinctiveness priority
    # [Implementation in app.py lines 5213-5237]
    
    # Build HTML table (returns string)
    # [Implementation in app.py lines 5239-5364]
    
    # Generate email body (returns string)
    # [Implementation in app.py lines 5391-5431]
    
    return report_df, email_body
```

---

## 4. HTML Table Structure (app.py, lines 5239-5364)

The HTML table uses this structure:

```python
html_table = """
<table border="1" style="border-collapse: collapse; width: 70%; margin: 0 auto; font-family: Arial, sans-serif; font-size: 11px;">
    <thead>
        <tr>
            <th colspan="3" style="text-align: center; padding: 8px; border: 1px solid #000; font-weight: bold; background-color: #F8C237; color: #000;">Development Impact</th>
            <th colspan="5" style="text-align: center; padding: 8px; border: 1px solid #000; font-weight: bold; background-color: #2A514A; color: #FFFFFF;">Mitigation Supplied from Wild Capital</th>
        </tr>
        <tr>
            <th style="...">Distinctiveness</th>
            <th style="...">Habitats Lost</th>
            <th style="..."># Units</th>
            <th style="...">Distinctiveness</th>
            <th style="...">Habitats Supplied</th>
            <th style="..."># Units</th>
            <th style="...">Price Per Unit</th>
            <th style="...">Offset Cost</th>
        </tr>
    </thead>
    <tbody>
        <!-- Area Habitats section (light green background) -->
        <!-- Hedgerow Habitats section -->
        <!-- Watercourse Habitats section -->
        <!-- Planning Discharge Pack row -->
        <!-- Total row -->
    </tbody>
</table>
"""
```

**Sections include:**
- Area Habitats (light green: `#D9F2D0`)
- Hedgerow Habitats
- Watercourse Habitats
- Planning Discharge Pack (admin fee)
- Total row

---

## 5. Email Body Generation (app.py, lines 5391-5437)

```python
# Dynamic intro text based on promoter selection
if promoter_name:
    intro_text = f"{promoter_name} has advised us that you need Biodiversity Net Gain units for your development in {location}, and we're here to help you discharge your BNG condition."
else:
    intro_text = f"Thank you for enquiring about BNG Units for your development in {location}"

email_body = f"""
<div style="font-family: Arial, sans-serif; font-size: 12px; line-height: 1.4;">

<strong>Dear {client_name}</strong>
<br><br>
<strong>Our Ref: {ref_number}</strong>
<br><br>
{intro_text}
<br><br>
<strong>About Us</strong>
<br><br>
Wild Capital is a national supplier of BNG Units and environmental mitigation credits...
<br><br>
<strong>Your Quote - £{total_with_admin:,.0f} + VAT</strong>
<br><br>
{html_table}
<br><br>
{next_steps}
</div>
"""
```

**The email includes:**
- Greeting with client name
- Reference number
- Dynamic intro based on promoter
- About Us section
- Quote total
- Full pricing table
- Next steps (different text for quotes < £10,000 vs >= £10,000)

---

## 6. Email Download Button (app.py, lines 6330-6392)

```python
# Create .eml file content
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

subject = f"RE: BNG Units for site at {location} - {ref_number}"
total_with_admin = session_total_cost + admin_fee_for_email

# Create email message
msg = MIMEMultipart('alternative')
msg['Subject'] = subject
msg['From'] = 'quotes@wildcapital.com'
msg['To'] = ''  # Will be filled by user

# Create text version for email clients that don't support HTML
text_body = f"""Dear {client_name}

Our Ref: {ref_number}

{intro_text}

About Us
Wild Capital is a national supplier of BNG Units...

Your Quote - £{total_with_admin:,.0f} + VAT

[Please view the HTML version for detailed pricing table]

Total Cost: £{total_with_admin:,.0f} + VAT

{next_steps}

Best regards,
Wild Capital Team"""

# Attach text and HTML versions
text_part = MIMEText(text_body, 'plain')
html_part = MIMEText(email_html, 'html')

msg.attach(text_part)
msg.attach(html_part)

# Convert to string
eml_content = msg.as_string()

# Download button for .eml file
st.download_button(
    "📧 Download Email (.eml)",
    data=eml_content,
    file_name=f"BNG_Quote_{ref_number}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.eml",
    mime="message/rfc822",
    help="Download as .eml file - double-click to open in your email client with full HTML formatting"
)
```

---

## 7. Call to `generate_client_report_table_fixed()` (app.py, lines 6290-6301)

```python
# Generate the report using session data and input values
client_table, email_html = generate_client_report_table_fixed(
    session_alloc_df, session_demand_df, session_total_cost, admin_fee_for_report,
    client_name, ref_number, location,
    st.session_state.manual_hedgerow_rows,
    st.session_state.manual_watercourse_rows,
    st.session_state.manual_area_rows,
    st.session_state.get("removed_allocation_rows", []),
    st.session_state.get("selected_promoter"),
    st.session_state.get("promoter_discount_type"),
    st.session_state.get("promoter_discount_value"),
    st.session_state.get("suo_discount_for_report", 0.0)
)
```

---

## 8. Sales & Quotes CSV Generation (sales_quotes_csv.py)

### Full Module: `sales_quotes_csv.py`

```python
"""
sales_quotes_csv.py - Generate CSV rows for Sales & Quotes Excel workbook.

This module converts optimiser allocation results into CSV data rows
that align with the Sales & Quotes Excel workbook column structure (A-BB).
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import pandas as pd

# Import constants from optimizer_core
from optimizer_core import ADMIN_FEE_GBP, ADMIN_FEE_FRACTIONAL_GBP

# Import database functions
from repo import fetch_banks


def get_admin_fee_for_contract_size(contract_size: str) -> float:
    """
    Get the admin fee based on contract size.
    Fractional quotes get £300, all others get £500.
    """
    if str(contract_size).lower().strip() == "fractional":
        return ADMIN_FEE_FRACTIONAL_GBP
    return ADMIN_FEE_GBP


def generate_sales_quotes_csv(
    quote_number: str,
    client_name: str,
    development_address: str,
    base_ref: str,
    introducer: Optional[str],
    today_date: datetime,
    local_planning_authority: str,
    national_character_area: str,
    allocations: List[Dict[str, Any]],
    contract_size: str = "small"
) -> str:
    """
    Generate CSV data rows (no headers) for the Sales & Quotes Excel workbook.
    
    Args:
        quote_number: Quote number (e.g., "1923")
        client_name: Client name (e.g., "David Evans")
        development_address: Single string for development address
        base_ref: Base reference (e.g., "BNG01640")
        introducer: Introducer name (or None for "Direct")
        today_date: Date for quote (will be formatted as DD/MM/YYYY)
        local_planning_authority: LPA name
        national_character_area: NCA name
        allocations: List of allocation dictionaries
        contract_size: Contract size for admin fee calculation
    
    Returns:
        CSV string with one line per allocation
    """
    csv_rows = []
    
    # Determine admin fee
    admin_fee = get_admin_fee_for_contract_size(contract_size)
    
    # Format date as DD/MM/YYYY
    quote_date_str = today_date.strftime("%d/%m/%Y")
    
    for alloc_idx, allocation in enumerate(allocations):
        # Extract allocation fields
        bank_ref = str(allocation.get("bank_ref", "")).strip()
        bank_name = str(allocation.get("bank_name", "")).strip()
        is_paired = bool(allocation.get("is_paired", False))
        spatial_relation = str(allocation.get("spatial_relation", "")).strip().lower()
        spatial_multiplier_numeric = allocation.get("spatial_multiplier_numeric", 1.0)
        habitats = allocation.get("habitats", [])[:8]  # Limit to 8 habitats
        
        # Create CSV row with 103 columns (A-CY)
        row = [""] * 103
        
        # Column B (index 1): Client
        row[1] = client_name.strip()
        
        # Column C (index 2): Address
        row[2] = development_address.strip().replace(',', ';')
        
        # Column D (index 3): Ref (with suffix if multiple allocations)
        if len(allocations) > 1:
            suffix = chr(ord('a') + alloc_idx)
            row[3] = f"{base_ref}{suffix}"
        else:
            row[3] = base_ref
        
        # Column AC (index 28): Habitat Bank / Source of Mitigation
        row[28] = f"{bank_ref[:5]} - {bank_name}" if bank_ref else bank_name
        
        # Column AD (index 29): Spatial Multiplier
        if is_paired:
            row[29] = "1"
        elif spatial_relation == "adjacent":
            row[29] = "=4/3"
        elif spatial_relation == "far":
            row[29] = "=2/1"
        else:
            row[29] = "1"
        
        # Column AH (index 33): Local Planning Authority
        row[33] = local_planning_authority.strip()
        
        # Column AI (index 34): National Character Area
        row[34] = national_character_area.strip()
        
        # Column AK (index 36): Introducer
        row[36] = introducer.strip() if introducer else "Direct"
        
        # Column AL (index 37): Quote Date
        row[37] = quote_date_str
        
        # Column AM (index 38): Quote Period (always "30")
        row[38] = "30"
        
        # Column AR (index 43): Admin Fee (only on first row)
        if alloc_idx == 0:
            row[43] = f"{admin_fee:.2f}"
        
        # Habitats 1-8 start at column AV (index 47)
        # Each habitat has 7 columns
        for hab_idx, habitat in enumerate(habitats):
            base_idx = 47 + (hab_idx * 7)
            
            # Column 0: Type
            row[base_idx] = str(habitat.get("type", "")).strip()
            
            # Column 1: # credits
            units_value = habitat.get("units_supplied", 0.0)
            row[base_idx + 1] = f"{units_value:.4f}"
            
            # Column 2: ST (Stock Take)
            st = spatial_multiplier_numeric * units_value
            row[base_idx + 2] = f"{st:.4f}"
            
            # Column 4: Quoted Price
            quoted_price = habitat.get("avg_effective_unit_price", 0.0)
            row[base_idx + 4] = f"{quoted_price:.2f}"
            
            # Column 6: Price inc SRM (Total Cost)
            habitat_total_cost = st * quoted_price
            row[base_idx + 6] = f"{habitat_total_cost:.2f}"
        
        # Convert row to CSV format
        csv_fields = []
        for field in row:
            field_str = str(field)
            if ',' in field_str or '"' in field_str or '\n' in field_str:
                field_str = '"' + field_str.replace('"', '""') + '"'
            csv_fields.append(field_str)
        
        csv_rows.append(','.join(csv_fields))
    
    return '\n'.join(csv_rows)


def generate_sales_quotes_csv_from_optimizer_output(
    quote_number: str,
    client_name: str,
    development_address: str,
    base_ref: str,
    introducer: Optional[str],
    today_date: datetime,
    local_planning_authority: str,
    national_character_area: str,
    alloc_df: pd.DataFrame,
    contract_size: str = "small"
) -> str:
    """
    Generate Sales & Quotes CSV from optimizer allocation DataFrame.
    
    This is a convenience wrapper that converts the optimizer's site_hab_totals DataFrame
    into CSV format.
    """
    # Group allocations by bank
    allocations = []
    
    if alloc_df.empty:
        return ""
    
    # Group by bank
    for bank_key, bank_group in alloc_df.groupby("BANK_KEY"):
        bank_name = bank_group["bank_name"].iloc[0]
        
        # Determine if paired allocation
        allocation_types = bank_group.get("allocation_type", pd.Series(["normal"]))
        is_paired = any(str(t).lower() == "paired" for t in allocation_types)
        
        # Get tier (spatial relation)
        tier = str(bank_group.get("tier", pd.Series(["far"])).iloc[0]).strip().lower()
        
        # Calculate spatial multiplier
        if tier == "local":
            spatial_multiplier_numeric = 1.0
        elif tier == "adjacent":
            spatial_multiplier_numeric = 4.0 / 3.0
        else:  # far
            spatial_multiplier_numeric = 2.0
        
        # Aggregate habitats
        habitats = []
        for _, row in bank_group.iterrows():
            habitat_type = str(row.get("supply_habitat", "")).strip()
            units_supplied = float(row.get("units_supplied", 0.0))
            effective_units = float(row.get("effective_units", units_supplied * spatial_multiplier_numeric))
            avg_effective_unit_price = float(row.get("avg_effective_unit_price", 0.0))
            
            if habitat_type:
                habitats.append({
                    "type": habitat_type,
                    "units_supplied": units_supplied,
                    "effective_units": effective_units,
                    "avg_effective_unit_price": avg_effective_unit_price
                })
        
        allocations.append({
            "bank_ref": str(bank_key),
            "bank_name": bank_name,
            "is_paired": is_paired,
            "spatial_relation": tier,
            "spatial_multiplier_numeric": spatial_multiplier_numeric,
            "habitats": habitats[:8]
        })
    
    return generate_sales_quotes_csv(
        quote_number=quote_number,
        client_name=client_name,
        development_address=development_address,
        base_ref=base_ref,
        introducer=introducer,
        today_date=today_date,
        local_planning_authority=local_planning_authority,
        national_character_area=national_character_area,
        allocations=allocations,
        contract_size=contract_size
    )
```

---

## 9. CSV Generation in UI (app.py, lines 6394-6441)

```python
# Generate Sales & Quotes CSV
st.markdown("---")
st.markdown("**📊 Sales & Quotes Database Export:**")
st.markdown("Generate CSV rows to paste into the Sales & Quotes Excel workbook.")

try:
    import sales_quotes_csv
    
    # Use site_hab_totals which has paired habitats already split
    site_hab_totals_df = st.session_state.get("site_hab_totals")
    
    if site_hab_totals_df is None or site_hab_totals_df.empty:
        st.info("No allocation data available for CSV export.")
    else:
        # Generate CSV from optimizer output
        csv_data = sales_quotes_csv.generate_sales_quotes_csv_from_optimizer_output(
            quote_number=ref_number,
            client_name=client_name,
            development_address=location,
            base_ref=ref_number,
            introducer=st.session_state.get("selected_promoter"),
            today_date=datetime.now(),
            local_planning_authority=st.session_state.get("target_lpa_name", ""),
            national_character_area=st.session_state.get("target_nca_name", ""),
            alloc_df=site_hab_totals_df,
            contract_size=st.session_state.get("contract_size", "small")
        )
        
        if csv_data:
            # Display CSV in a code block with copy button
            st.code(csv_data, language=None, line_numbers=False)
            st.caption("👆 Click the copy button to copy CSV data to clipboard")
            
            # Download option
            st.download_button(
                "💾 Download as CSV file (backup option)",
                data=csv_data,
                file_name=f"Sales_Quotes_{ref_number}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
except Exception as e:
    st.error(f"Error generating Sales & Quotes CSV: {e}")
```

---

## Complete Call Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    OPTIMIZATION COMPLETES                                │
│  st.session_state["last_alloc_df"] = allocation results                  │
│  st.session_state["optimization_complete"] = True                        │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    USER ENTERS CLIENT DETAILS                            │
│  Client Name, Location, Customer Email/Mobile (optional)                 │
│  Click "Update Email Details" button                                     │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              generate_client_report_table_fixed()                        │
│  Inputs:                                                                 │
│    - alloc_df (allocation results)                                       │
│    - demand_df (habitat demand)                                          │
│    - total_cost, admin_fee                                              │
│    - client_name, ref_number, location                                   │
│    - manual_*_rows (hedgerow, watercourse, area)                        │
│    - removed_allocation_rows                                             │
│    - promoter_name, discount_type, discount_value                        │
│    - suo_discount_fraction                                               │
│                                                                          │
│  Processing:                                                             │
│    1. Categorize habitats (area/hedgerow/watercourse)                    │
│    2. Process manual entries                                             │
│    3. Apply SUO discount                                                 │
│    4. Round prices (£50 increments)                                      │
│    5. Bundle Low + 10% Net Gain rows                                     │
│    6. Sort by distinctiveness priority                                   │
│    7. Build HTML table                                                   │
│    8. Generate email body                                                │
│                                                                          │
│  Returns: (report_df, email_html)                                        │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌───────────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐
│  Display Table in UI  │ │  Create .eml     │ │  Generate CSV            │
│  st.dataframe(...)    │ │  MIMEMultipart   │ │  sales_quotes_csv.py     │
│                       │ │  + text + html   │ │  generate_sales_quotes_  │
│                       │ │                  │ │  csv_from_optimizer_     │
│                       │ │                  │ │  output()                │
└───────────────────────┘ └────────┬─────────┘ └────────────┬─────────────┘
                                   │                        │
                                   ▼                        ▼
                          ┌────────────────┐      ┌────────────────────┐
                          │ Download .eml  │      │ Display CSV +      │
                          │ Button         │      │ Download Button    │
                          └────────────────┘      └────────────────────┘
```

---

## Summary

### Client Report Table (`generate_client_report_table_fixed`)
- **Input**: Allocation DataFrame, demand DataFrame, costs, client info, manual entries
- **Processing**: Categorizes habitats, applies discounts, rounds prices, builds HTML
- **Output**: Tuple of (DataFrame for display, HTML string for email)

### Email Generation
- Creates MIMEMultipart message with both plain text and HTML versions
- Includes dynamic intro based on promoter selection
- Different "Next Steps" text based on quote amount (< £10,000 vs >= £10,000)
- Downloads as .eml file

### CSV Generation (`sales_quotes_csv.py`)
- Uses `site_hab_totals` DataFrame (already has paired habitats split)
- Groups by bank, calculates spatial multipliers
- Generates CSV aligned with Sales & Quotes Excel workbook (columns A-CY)
- Includes client info, allocation details, pricing, admin fee
