# Extracted Promoter Discount Code

This document contains the exact code from `app.py` and `database.py` that deals with promoters/introducers and their discounts.

---

## 1. Promoter/Introducer Table Schema (database.py, lines 591-604)

This creates the `introducers` table in the database:

```python
# Introducers/Promoters table
conn.execute(text("""
    CREATE TABLE IF NOT EXISTS introducers (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        username TEXT UNIQUE,
        password_hash TEXT,
        password_salt TEXT,
        parent_introducer_id INTEGER REFERENCES introducers(id),
        discount_type TEXT NOT NULL CHECK(discount_type IN ('tier_up', 'percentage', 'no_discount')),
        discount_value FLOAT NOT NULL,
        created_date TIMESTAMP NOT NULL,
        updated_date TIMESTAMP NOT NULL
    )
"""))
```

---

## 2. Session State Initialization for Promoters (app.py, lines 131-135)

```python
# In init_session_state() function defaults:
"use_promoter": False,
"selected_promoter": None,
"promoter_discount_type": None,
"promoter_discount_value": None,
```

---

## 3. Promoter Selection UI (app.py, lines 2240-2293)

This is the UI section where users select a promoter:

```python
# ================= Promoter/Introducer Selection =================
st.markdown("---")
with st.container():
    st.subheader("2) Promoter/Introducer (Optional)")
    
    # Get introducers from database
    try:
        introducers_list = db.get_all_introducers() if db else []
        introducer_names = [intro['name'] for intro in introducers_list]
    except Exception as e:
        st.error(f"Error loading introducers: {e}")
        introducers_list = []
        introducer_names = []
    
    col1, col2 = st.columns([1, 2])
    with col1:
        use_promoter = st.checkbox("Use Promoter/Introducer", 
                                    value=st.session_state.get("use_promoter", False),
                                    key="use_promoter_checkbox")
        st.session_state["use_promoter"] = use_promoter
    
    with col2:
        if use_promoter:
            if not introducer_names:
                st.warning("⚠️ No introducers configured. Please add introducers in the Admin Dashboard.")
                st.session_state["selected_promoter"] = None
                st.session_state["promoter_discount_type"] = None
                st.session_state["promoter_discount_value"] = None
            else:
                selected = st.selectbox("Select Introducer",
                                       introducer_names,
                                       key="promoter_dropdown",
                                       help="Select an approved introducer to apply their discount")
                
                # Store selected promoter details in session state
                if selected:
                    selected_intro = next((intro for intro in introducers_list if intro['name'] == selected), None)
                    if selected_intro:
                        st.session_state["selected_promoter"] = selected_intro['name']
                        st.session_state["promoter_discount_type"] = selected_intro['discount_type']
                        st.session_state["promoter_discount_value"] = selected_intro['discount_value']
                        
                        # Show discount info
                        if selected_intro['discount_type'] == 'tier_up':
                            st.info(f"💡 **Tier Up Discount**: Pricing uses one contract size tier higher (e.g., fractional → small, small → medium, medium → large) for better rates")
                        elif selected_intro['discount_type'] == 'percentage':
                            st.info(f"💡 **Percentage Discount**: {selected_intro['discount_value']}% discount on all items except £500 admin fee")
                        else:  # no_discount
                            st.info(f"💡 **No Discount Applied**: Promoter registered for dynamic email text only")
        else:
            st.session_state["selected_promoter"] = None
            st.session_state["promoter_discount_type"] = None
            st.session_state["promoter_discount_value"] = None
```

---

## 4. Discount Application Functions (app.py, lines 2970-3021)

These are the core functions that apply discounts:

```python
def apply_tier_up_discount(contract_size: str, available_sizes: List[str]) -> str:
    """
    Apply tier_up discount: move contract size one level up.
    fractional -> small -> medium -> large
    
    This gives better (lower) pricing by using a larger contract size's rates.
    The actual contract size remains unchanged for the quote.
    """
    size_lower = contract_size.lower()
    available_lower = [s.lower() for s in available_sizes]
    
    # Define the hierarchy from smallest to largest
    size_hierarchy = ["fractional", "small", "medium", "large"]
    
    # Find current position
    try:
        current_index = size_hierarchy.index(size_lower)
    except ValueError:
        # If size not in hierarchy, return as-is
        return contract_size
    
    # Move up one level (to next larger size)
    for next_index in range(current_index + 1, len(size_hierarchy)):
        next_size = size_hierarchy[next_index]
        if next_size in available_lower:
            return next_size
    
    # If no larger size available, return current size
    return contract_size


def apply_percentage_discount(unit_price: float, discount_percentage: float) -> float:
    """
    Apply percentage discount to unit price.
    discount_percentage is in percent (e.g., 10.0 for 10%)
    """
    return unit_price * (1.0 - discount_percentage / 100.0)


def get_active_promoter_discount():
    """
    Get active promoter discount settings from session state.
    Returns (discount_type, discount_value) or (None, None) if no promoter selected.
    """
    if not st.session_state.get("use_promoter", False):
        return None, None
    
    discount_type = st.session_state.get("promoter_discount_type")
    discount_value = st.session_state.get("promoter_discount_value")
    
    if discount_type and discount_value is not None:
        return discount_type, discount_value
    
    return None, None
```

---

## 5. Usage of Promoter Discount in `prepare_options()` (app.py, lines 3062-3068, 3245-3249)

**Getting active discount settings:**

```python
# Get active promoter discount settings
promoter_discount_type, promoter_discount_value = get_active_promoter_discount()

# Apply tier_up discount to contract size if active
pricing_contract_size = chosen_size
if promoter_discount_type == "tier_up":
    available_sizes = Pricing["contract_size"].drop_duplicates().tolist()
    pricing_contract_size = apply_tier_up_discount(chosen_size, available_sizes)
```

**Applying percentage discount to unit price:**

```python
# Apply percentage discount if active
if promoter_discount_type == "percentage" and promoter_discount_value:
    unit_price = apply_percentage_discount(unit_price, promoter_discount_value)
```

---

## 6. Usage in Hedgerow Options (app.py, lines 3439-3446, 3526-3528)

```python
# Get active promoter discount settings
promoter_discount_type, promoter_discount_value = get_active_promoter_discount()

# Apply tier_up discount to contract size if active
pricing_contract_size = chosen_size
if promoter_discount_type == "tier_up":
    available_sizes = Pricing["contract_size"].drop_duplicates().tolist()
    pricing_contract_size = apply_tier_up_discount(chosen_size, available_sizes)

# ... later in the code ...

# Apply percentage discount if active
if promoter_discount_type == "percentage" and promoter_discount_value:
    price = apply_percentage_discount(price, promoter_discount_value)
```

---

## 7. Usage in Watercourse Options (app.py, lines 3592-3598, 3701-3703)

```python
# Get active promoter discount settings
promoter_discount_type, promoter_discount_value = get_active_promoter_discount()

# Apply tier_up discount to contract size if active
pricing_contract_size = chosen_size
if promoter_discount_type == "tier_up":
    available_sizes = Pricing["contract_size"].drop_duplicates().tolist()
    pricing_contract_size = apply_tier_up_discount(chosen_size, available_sizes)

# ... later in the code ...

# Apply percentage discount if active
if promoter_discount_type == "percentage" and promoter_discount_value:
    price = apply_percentage_discount(price, promoter_discount_value)
```

---

## 8. Usage in Paired Allocations (app.py, lines 3366-3369)

```python
# Apply percentage discount if active (to blended price)
if promoter_discount_type == "percentage" and promoter_discount_value:
    blended_price = apply_percentage_discount(blended_price, promoter_discount_value)
```

---

## 9. Introducers CRUD Operations (database.py, lines 1134-1389)

### Add Introducer:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((Exception,)),
    reraise=True
)
def add_introducer(self, name: str, discount_type: str, discount_value: float,
                   username: Optional[str] = None, password: Optional[str] = None,
                   parent_introducer_id: Optional[int] = None) -> int:
    """
    Add a new introducer/promoter with optional username/password.
    
    Args:
        name: Display name for the introducer
        discount_type: Type of discount ('tier_up', 'percentage', 'no_discount')
        discount_value: Value of discount
        username: Optional login username
        password: Optional plain text password (will be hashed)
        parent_introducer_id: Optional ID of parent introducer (for child accounts)
    
    Returns:
        ID of the created introducer
    """
    engine = self._get_connection()
    
    now = datetime.now()
    
    # Hash password if provided
    password_hash = None
    password_salt = None
    if password:
        password_hash, password_salt = hash_password(password)
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            result = conn.execute(text("""
                INSERT INTO introducers (name, username, password_hash, password_salt, 
                                        parent_introducer_id,
                                        discount_type, discount_value, created_date, updated_date)
                VALUES (:name, :username, :password_hash, :password_salt,
                        :parent_introducer_id,
                        :discount_type, :discount_value, :created_date, :updated_date)
                RETURNING id
            """), {
                "name": name,
                "username": username,
                "password_hash": password_hash,
                "password_salt": password_salt,
                "parent_introducer_id": parent_introducer_id,
                "discount_type": discount_type,
                "discount_value": discount_value,
                "created_date": now,
                "updated_date": now
            })
            
            introducer_id = result.fetchone()[0]
            trans.commit()
            return introducer_id
        except Exception as e:
            trans.rollback()
            raise
```

### Get All Introducers:

```python
def get_all_introducers(self) -> List[Dict[str, Any]]:
    """Get all introducers."""
    engine = self._get_connection()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM introducers ORDER BY name"))
        rows = result.fetchall()
        
        return [dict(row._mapping) for row in rows]
```

### Get Introducer by ID:

```python
def get_introducer_by_id(self, introducer_id: int) -> Optional[Dict[str, Any]]:
    """Get an introducer by ID."""
    engine = self._get_connection()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM introducers WHERE id = :id"),
            {"id": introducer_id}
        )
        row = result.fetchone()
        
        if row:
            return dict(row._mapping)
        return None
```

### Get Introducer by Name:

```python
def get_introducer_by_name(self, name: str) -> Optional[Dict[str, Any]]:
    """Get an introducer by name."""
    engine = self._get_connection()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM introducers WHERE name = :name"),
            {"name": name}
        )
        row = result.fetchone()
        
        if row:
            return dict(row._mapping)
        return None
```

### Update Introducer:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((Exception,)),
    reraise=True
)
def update_introducer(self, introducer_id: int, name: str, discount_type: str, discount_value: float):
    """Update an existing introducer."""
    engine = self._get_connection()
    
    now = datetime.now()
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            conn.execute(text("""
                UPDATE introducers 
                SET name = :name, discount_type = :discount_type, 
                    discount_value = :discount_value, updated_date = :updated_date
                WHERE id = :id
            """), {
                "name": name,
                "discount_type": discount_type,
                "discount_value": discount_value,
                "updated_date": now,
                "id": introducer_id
            })
            
            trans.commit()
        except Exception as e:
            trans.rollback()
            raise
```

### Delete Introducer:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((Exception,)),
    reraise=True
)
def delete_introducer(self, introducer_id: int):
    """Delete an introducer."""
    engine = self._get_connection()
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            conn.execute(
                text("DELETE FROM introducers WHERE id = :id"),
                {"id": introducer_id}
            )
            
            trans.commit()
        except Exception as e:
            trans.rollback()
            raise
```

---

## 10. Admin Dashboard - Introducer Management UI (app.py, lines 469-577)

This is the Admin Dashboard UI section for managing introducers:

```python
# ================= Introducer Management =================
st.markdown("#### 👥 Introducer/Promoter Management")

# Get all introducers
try:
    introducers = db.get_all_introducers()
    
    # Add new introducer
    with st.expander("➕ Add New Introducer", expanded=False):
        with st.form("add_introducer_form"):
            new_name = st.text_input("Introducer Name", key="new_introducer_name")
            new_discount_type = st.selectbox("Discount Type", ["tier_up", "percentage", "no_discount"], key="new_discount_type")
            new_discount_value = st.number_input("Discount Value", 
                                                 min_value=0.0, 
                                                 step=0.1,
                                                 key="new_discount_value",
                                                 help="For percentage: enter as decimal (e.g., 10.5 for 10.5%). For tier_up or no_discount: value is ignored.",
                                                 disabled=(st.session_state.get("new_discount_type") == "no_discount"))
            add_submit = st.form_submit_button("Add Introducer")
            
            if add_submit:
                if not new_name or not new_name.strip():
                    st.error("Please enter an introducer name.")
                else:
                    try:
                        # For no_discount type, set value to 0
                        discount_value = 0.0 if st.session_state.get("new_discount_type") == "no_discount" else new_discount_value
                        db.add_introducer(new_name.strip(), new_discount_type, discount_value)
                        st.success(f"✅ Added introducer: {new_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding introducer: {e}")
    
    # Display existing introducers
    if introducers:
        st.markdown("##### Current Introducers")
        for intro in introducers:
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
            with col1:
                st.write(f"**{intro['name']}**")
            with col2:
                st.write(f"Type: {intro['discount_type']}")
            with col3:
                if intro['discount_type'] == 'percentage':
                    st.write(f"Value: {intro['discount_value']}%")
                elif intro['discount_type'] == 'no_discount':
                    st.write("No Discount")
                else:
                    st.write("Tier Up")
            with col4:
                # Edit button - use unique key with introducer id
                if st.button("✏️", key=f"edit_{intro['id']}", help="Edit"):
                    st.session_state[f"editing_introducer_{intro['id']}"] = True
            with col5:
                # Delete button
                if st.button("🗑️", key=f"delete_{intro['id']}", help="Delete"):
                    try:
                        db.delete_introducer(intro['id'])
                        st.success(f"Deleted: {intro['name']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting: {e}")
            
            # Edit form (shown when edit button is clicked)
            if st.session_state.get(f"editing_introducer_{intro['id']}", False):
                with st.form(f"edit_form_{intro['id']}"):
                    edit_name = st.text_input("Name", value=intro['name'], key=f"edit_name_{intro['id']}")
                    edit_discount_type = st.selectbox("Discount Type", 
                                                     ["tier_up", "percentage", "no_discount"],
                                                     index=0 if intro['discount_type'] == 'tier_up' else (1 if intro['discount_type'] == 'percentage' else 2),
                                                     key=f"edit_type_{intro['id']}")
                    edit_discount_value = st.number_input("Discount Value",
                                                         value=float(intro['discount_value']),
                                                         min_value=0.0,
                                                         step=0.1,
                                                         key=f"edit_value_{intro['id']}",
                                                         disabled=(edit_discount_type == "no_discount"))
                    
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        save_btn = st.form_submit_button("💾 Save")
                    with col_cancel:
                        cancel_btn = st.form_submit_button("❌ Cancel")
                    
                    if save_btn:
                        if not edit_name or not edit_name.strip():
                            st.error("Please enter a name.")
                        else:
                            try:
                                # For no_discount type, set value to 0
                                discount_value = 0.0 if edit_discount_type == "no_discount" else edit_discount_value
                                db.update_introducer(intro['id'], edit_name.strip(), edit_discount_type, discount_value)
                                st.success(f"Updated: {edit_name}")
                                st.session_state[f"editing_introducer_{intro['id']}"] = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating: {e}")
                    
                    if cancel_btn:
                        st.session_state[f"editing_introducer_{intro['id']}"] = False
                        st.rerun()
    else:
        st.info("No introducers added yet. Add one using the form above.")

except Exception as e:
    st.error(f"Error loading introducers: {e}")
    import traceback
    st.code(traceback.format_exc())
```

---

## 11. Storing Promoter Info with Submission (app.py, lines 6256-6258)

When a submission is stored, promoter information is included:

```python
submission_id = db.store_submission(
    # ... other parameters ...
    promoter_name=st.session_state.get("selected_promoter"),
    promoter_discount_type=st.session_state.get("promoter_discount_type"),
    promoter_discount_value=st.session_state.get("promoter_discount_value"),
    # ... other parameters ...
)
```

---

## Summary

The promoter/introducer discount system works as follows:

### Discount Types:
1. **tier_up**: Uses pricing from the next higher contract size tier (fractional→small→medium→large)
2. **percentage**: Applies a percentage discount to unit prices (e.g., 10% off)
3. **no_discount**: No pricing discount - used for tracking introducers without pricing benefits

### Flow:
1. Admin creates introducers in the Admin Dashboard with their discount type and value
2. User selects a promoter/introducer in the quote form UI
3. Selection is stored in session state
4. During optimization, `get_active_promoter_discount()` retrieves the active settings
5. For tier_up: `apply_tier_up_discount()` modifies the contract size used for pricing
6. For percentage: `apply_percentage_discount()` reduces each unit price
7. When quote is saved, promoter info is stored with the submission

### Database Tables:
- `introducers` table stores all promoter/introducer records
- `submissions` table has columns for `promoter_name`, `promoter_discount_type`, and `promoter_discount_value`
