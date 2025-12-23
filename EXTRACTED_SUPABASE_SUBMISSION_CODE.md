# Extracted Supabase Submission Code

This document contains the exact code from `app.py` and `database.py` that deals with pushing submission data to Supabase into the `submissions` table.

---

## 1. Database Schema and Table Creation (database.py, lines 134-188)

This code creates the `submissions` table in Supabase/PostgreSQL:

```python
# Main submissions table
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS submissions (
            id SERIAL PRIMARY KEY,
            submission_date TIMESTAMP NOT NULL,
            
            -- Client details
            client_name TEXT,
            reference_number TEXT,
            site_location TEXT,
            
            -- Location metadata
            target_lpa TEXT,
            target_nca TEXT,
            target_lat FLOAT,
            target_lon FLOAT,
            lpa_neighbors TEXT[],
            nca_neighbors TEXT[],
            
            -- Form inputs (demand)
            demand_habitats JSONB,
            
            -- Optimization metadata
            contract_size TEXT,
            total_cost FLOAT,
            admin_fee FLOAT,
            total_with_admin FLOAT,
            num_banks_selected INTEGER,
            banks_used TEXT[],
            
            -- Manual entries
            manual_hedgerow_entries JSONB,
            manual_watercourse_entries JSONB,
            manual_area_habitat_entries JSONB,
            
            -- Full allocation results (JSON)
            allocation_results JSONB,
            
            -- User info
            username TEXT,
            
            -- Promoter/Introducer info
            promoter_name TEXT,
            promoter_discount_type TEXT,
            promoter_discount_value FLOAT,
            
            -- Surplus Uplift Offset (SUO) info
            suo_enabled BOOLEAN DEFAULT FALSE,
            suo_discount_fraction FLOAT,
            suo_eligible_surplus FLOAT,
            suo_usable_surplus FLOAT,
            suo_total_units FLOAT
        )
    """))
```

---

## 2. Database Indexes for Submissions (database.py, lines 191-207)

```python
# Create indexes for submissions table
with engine.begin() as conn:
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_submissions_date 
        ON submissions(submission_date DESC)
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_submissions_client 
        ON submissions(client_name)
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_submissions_lpa 
        ON submissions(target_lpa)
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_submissions_nca 
        ON submissions(target_nca)
    """))
```

---

## 3. The `store_submission` Method (database.py, lines 816-1002)

This is the main method that pushes submission data to Supabase:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((Exception,)),
    reraise=True
)
def store_submission(self, 
                    client_name: str,
                    reference_number: str,
                    site_location: str,
                    target_lpa: str,
                    target_nca: str,
                    target_lat: Optional[float],
                    target_lon: Optional[float],
                    lpa_neighbors: List[str],
                    nca_neighbors: List[str],
                    demand_df: pd.DataFrame,
                    allocation_df: pd.DataFrame,
                    contract_size: str,
                    total_cost: float,
                    admin_fee: float,
                    manual_hedgerow_rows: List[Dict],
                    manual_watercourse_rows: List[Dict],
                    manual_area_habitat_rows: Optional[List[Dict]] = None,
                    username: str = "",
                    promoter_name: Optional[str] = None,
                    promoter_discount_type: Optional[str] = None,
                    promoter_discount_value: Optional[float] = None,
                    customer_id: Optional[int] = None,
                    suo_enabled: bool = False,
                    suo_discount_fraction: Optional[float] = None,
                    suo_eligible_surplus: Optional[float] = None,
                    suo_usable_surplus: Optional[float] = None,
                    suo_total_units: Optional[float] = None,
                    submitted_by_username: Optional[str] = None,
                    contact_email: Optional[str] = None,
                    contact_number: Optional[str] = None) -> int:
    """
    Store a complete submission to the database.
    Returns the submission_id for reference.
    
    Args:
        ...
        submitted_by_username: Username of the individual who submitted this quote
                               (may differ from promoter_name for child accounts)
        contact_email: Client's email address for contact
        contact_number: Client's phone number for contact
    
    Uses transactions and automatic retry on transient failures.
    """
    engine = self._get_connection()
    
    # Prepare data
    submission_date = datetime.now()
    total_with_admin = float(total_cost) + float(admin_fee)
    
    # Banks used - ensure it's a proper list of strings
    banks_used = allocation_df["BANK_KEY"].unique().tolist() if not allocation_df.empty else []
    banks_used = [str(bank) for bank in banks_used]  # Ensure all are strings
    num_banks = len(banks_used)
    
    # Sanitize array fields - convert to JSON strings for JSONB columns
    lpa_neighbors_json = json.dumps([str(item) for item in lpa_neighbors]) if lpa_neighbors else json.dumps([])
    nca_neighbors_json = json.dumps([str(item) for item in nca_neighbors]) if nca_neighbors else json.dumps([])
    banks_used_json = json.dumps([str(bank) for bank in banks_used])
    
    # Convert DataFrames to JSON for JSONB storage
    # Sanitize to ensure all numpy/Decimal types are converted
    demand_habitats_json = json.loads(demand_df.to_json(orient='records')) if not demand_df.empty else []
    demand_habitats_json = sanitize_for_db(demand_habitats_json)
    
    allocation_results_json = json.loads(allocation_df.to_json(orient='records')) if not allocation_df.empty else []
    allocation_results_json = sanitize_for_db(allocation_results_json)
    
    # Sanitize manual entries
    manual_hedgerow_rows_clean = sanitize_for_db(manual_hedgerow_rows)
    manual_watercourse_rows_clean = sanitize_for_db(manual_watercourse_rows)
    manual_area_habitat_rows_clean = sanitize_for_db(manual_area_habitat_rows) if manual_area_habitat_rows else []
    
    # Sanitize numeric fields
    target_lat_clean = float(target_lat) if target_lat is not None else None
    target_lon_clean = float(target_lon) if target_lon is not None else None
    total_cost_clean = float(total_cost)
    admin_fee_clean = float(admin_fee)
    promoter_discount_value_clean = float(promoter_discount_value) if promoter_discount_value is not None else None
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        try:
            # Insert main submission
            result = conn.execute(text("""
                INSERT INTO submissions (
                    submission_date, client_name, reference_number, site_location,
                    target_lpa, target_nca, target_lat, target_lon,
                    lpa_neighbors, nca_neighbors, demand_habitats,
                    contract_size, total_cost, admin_fee, total_with_admin,
                    num_banks_selected, banks_used,
                    manual_hedgerow_entries, manual_watercourse_entries, manual_area_habitat_entries,
                    allocation_results, username,
                    promoter_name, promoter_discount_type, promoter_discount_value,
                    customer_id,
                    suo_enabled, suo_discount_fraction, suo_eligible_surplus, suo_usable_surplus, suo_total_units,
                    submitted_by_username, contact_email, contact_number
                ) VALUES (
                    :submission_date, :client_name, :reference_number, :site_location,
                    :target_lpa, :target_nca, :target_lat, :target_lon,
                    :lpa_neighbors, :nca_neighbors, :demand_habitats,
                    :contract_size, :total_cost, :admin_fee, :total_with_admin,
                    :num_banks_selected, :banks_used,
                    :manual_hedgerow_entries, :manual_watercourse_entries, :manual_area_habitat_entries,
                    :allocation_results, :username,
                    :promoter_name, :promoter_discount_type, :promoter_discount_value,
                    :customer_id,
                    :suo_enabled, :suo_discount_fraction, :suo_eligible_surplus, :suo_usable_surplus, :suo_total_units,
                    :submitted_by_username, :contact_email, :contact_number
                ) RETURNING id
            """), {
                "submission_date": submission_date,
                "client_name": client_name,
                "reference_number": reference_number,
                "site_location": site_location,
                "target_lpa": target_lpa,
                "target_nca": target_nca,
                "target_lat": target_lat_clean,
                "target_lon": target_lon_clean,
                "lpa_neighbors": lpa_neighbors_json,  # JSONB
                "nca_neighbors": nca_neighbors_json,  # JSONB
                "demand_habitats": json.dumps(demand_habitats_json),  # JSONB
                "contract_size": contract_size,
                "total_cost": total_cost_clean,
                "admin_fee": admin_fee_clean,
                "total_with_admin": total_with_admin,
                "num_banks_selected": num_banks,
                "banks_used": banks_used_json,  # JSONB
                "manual_hedgerow_entries": json.dumps(manual_hedgerow_rows_clean),  # JSONB
                "manual_watercourse_entries": json.dumps(manual_watercourse_rows_clean),  # JSONB
                "manual_area_habitat_entries": json.dumps(manual_area_habitat_rows_clean),  # JSONB
                "allocation_results": json.dumps(allocation_results_json),  # JSONB
                "username": username,
                "promoter_name": promoter_name,
                "promoter_discount_type": promoter_discount_type,
                "promoter_discount_value": promoter_discount_value_clean,
                "customer_id": customer_id,
                "suo_enabled": suo_enabled,
                "suo_discount_fraction": float(suo_discount_fraction) if suo_discount_fraction is not None else None,
                "suo_eligible_surplus": float(suo_eligible_surplus) if suo_eligible_surplus is not None else None,
                "suo_usable_surplus": float(suo_usable_surplus) if suo_usable_surplus is not None else None,
                "suo_total_units": float(suo_total_units) if suo_total_units is not None else None,
                "submitted_by_username": submitted_by_username,
                "contact_email": contact_email,
                "contact_number": contact_number
            })
            
            submission_id = result.fetchone()[0]
            
            # Insert allocation details
            if not allocation_df.empty:
                for _, row in allocation_df.iterrows():
                    # Sanitize row data
                    row_dict = {
                        "submission_id": submission_id,
                        "bank_key": str(row.get("BANK_KEY", "")),
                        "bank_name": str(row.get("bank_name", "")),
                        "demand_habitat": str(row.get("demand_habitat", "")),
                        "supply_habitat": str(row.get("supply_habitat", "")),
                        "allocation_type": str(row.get("allocation_type", "")),
                        "tier": str(row.get("proximity", "")),
                        "units_supplied": float(sanitize_for_db(row.get("units_supplied", 0.0))),
                        "unit_price": float(sanitize_for_db(row.get("unit_price", 0.0))),
                        "cost": float(sanitize_for_db(row.get("cost", 0.0)))
                    }
                    
                    conn.execute(text("""
                        INSERT INTO allocation_details (
                            submission_id, bank_key, bank_name,
                            demand_habitat, supply_habitat, allocation_type,
                            tier, units_supplied, unit_price, cost
                        ) VALUES (
                            :submission_id, :bank_key, :bank_name,
                            :demand_habitat, :supply_habitat, :allocation_type,
                            :tier, :units_supplied, :unit_price, :cost
                        )
                    """), row_dict)
            
            # Commit transaction
            trans.commit()
            return submission_id
            
        except Exception as e:
            # Rollback on error
            trans.rollback()
            raise
```

---

## 4. Sanitize Helper Function for Database (database.py, lines 57-105)

```python
def sanitize_for_db(value: Any) -> Any:
    """
    Sanitize a value for database insertion.
    
    Converts:
    - numpy numeric types to native Python types
    - Decimal to float
    - Ensures proper JSON serialization
    - Handles None values
    
    Args:
        value: Value to sanitize
    
    Returns:
        Sanitized value ready for database insertion
    """
    if value is None:
        return None
    
    # Check for NaN/inf in regular floats first (np.nan is actually a Python float)
    if isinstance(value, float):
        if np.isnan(value) or np.isinf(value):
            return None
        return value
    
    # Convert numpy types to native Python types
    if isinstance(value, (np.integer, np.int64, np.int32)):
        return int(value)
    elif isinstance(value, (np.floating, np.float64, np.float32)):
        # Check for NaN or inf
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)
    elif isinstance(value, np.bool_):
        return bool(value)
    
    # Convert Decimal to float
    elif isinstance(value, Decimal):
        return float(value)
    
    # Handle lists recursively
    elif isinstance(value, list):
        return [sanitize_for_db(item) for item in value]
    
    # Handle dicts recursively
    elif isinstance(value, dict):
        return {key: sanitize_for_db(val) for key, val in value.items()}
    
    return value
```

---

## 5. Call to `store_submission` from app.py (app.py, lines 6237-6274)

This is the actual call in the Streamlit UI that triggers the database save:

```python
submission_id = db.store_submission(
    client_name=form_client_name,
    reference_number=auto_ref_number,
    site_location=form_location,
    target_lpa=st.session_state.get("target_lpa_name", ""),
    target_nca=st.session_state.get("target_nca_name", ""),
    target_lat=st.session_state.get("target_lat"),
    target_lon=st.session_state.get("target_lon"),
    lpa_neighbors=st.session_state.get("lpa_neighbors", []),
    nca_neighbors=st.session_state.get("nca_neighbors", []),
    demand_df=session_demand_df,
    allocation_df=session_alloc_df,
    contract_size=contract_size_val,
    total_cost=session_total_cost,
    admin_fee=admin_fee_for_quote,
    manual_hedgerow_rows=st.session_state.get("manual_hedgerow_rows", []),
    manual_watercourse_rows=st.session_state.get("manual_watercourse_rows", []),
    manual_area_habitat_rows=st.session_state.get("manual_area_habitat_rows", []),
    username=current_user,
    promoter_name=st.session_state.get("selected_promoter"),
    promoter_discount_type=st.session_state.get("promoter_discount_type"),
    promoter_discount_value=st.session_state.get("promoter_discount_value"),
    customer_id=customer_id,
    suo_enabled=st.session_state.get("suo_enabled", False),
    suo_discount_fraction=(st.session_state.get("suo_results") or {}).get("discount_fraction"),
    suo_eligible_surplus=(st.session_state.get("suo_results") or {}).get("eligible_surplus"),
    suo_usable_surplus=(st.session_state.get("suo_results") or {}).get("usable_surplus"),
    suo_total_units=(st.session_state.get("suo_results") or {}).get("total_units_purchased")
)
st.success(f"✅ Quote saved to database! Submission ID: {submission_id}")
st.info(f"📊 Client: {form_client_name} | Reference: **{auto_ref_number}** | Total: £{session_total_cost + admin_fee_for_quote:,.0f}")

# Store the generated reference for use in report generation
st.session_state.email_ref_number = auto_ref_number
```

---

## 6. Auto-Generate Reference Number (database.py, lines 1708-1748)

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

---

## 7. Database Connection (from db.py)

The database connection is managed through the `DatabaseConnection` class which uses Streamlit secrets for Supabase/PostgreSQL connection:

```python
# In database.py, line 122-125
def _get_connection(self):
    """Get database connection from the engine."""
    # Return the engine for compatibility, actual connections are managed by SQLAlchemy
    return DatabaseConnection.get_engine()
```

---

## Summary

The submission flow is:
1. User fills in the form in app.py UI
2. User clicks "Update Email Details" button which triggers form submission
3. `db.get_next_bng_reference()` is called to auto-generate a reference number
4. `db.store_submission()` is called with all the data
5. The method sanitizes all data, creates a transaction, inserts into `submissions` table
6. It also inserts related allocation details into `allocation_details` table
7. Transaction is committed and submission_id is returned

The database uses PostgreSQL/Supabase with SQLAlchemy for connection management.
