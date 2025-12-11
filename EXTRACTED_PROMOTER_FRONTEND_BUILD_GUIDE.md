# Promoter Frontend Build Guide

## Overview

You need to build a **separate frontend for promoters with login authentication**. This is different from the office version (`app.py`) which has full admin access. The promoter frontend (`promoter_app.py`) provides a restricted interface for promoters/introducers to submit quote requests on behalf of clients.

---

## Architecture

### Two Separate Frontends

1. **Office Version (`app.py`)** - Full access, no login required
   - Complete BNG metric upload
   - All optimization features
   - Direct access to all database operations
   - Admin dashboard features

2. **Promoter Version (`promoter_app.py`)** - Restricted access with login
   - Login authentication system
   - Quote request submission only
   - Automated quote generation
   - Password management
   - Quote history viewing

---

## Key Requirements for Promoter Frontend

### 1. Authentication System

**Database Table: `introducers`**
- Stores promoter accounts with hashed passwords
- Parent/child account support for organizations
- Discount settings per promoter

**Authentication Flow:**
```
1. User enters username + password
2. Hash password using bcrypt
3. Query introducers table for matching credentials
4. If child account, load parent info for discount settings
5. Set session state with promoter info
```

**Key Functions:**
- `authenticate_promoter(username, password)` → Returns (bool, promoter_info)
- Uses bcrypt password hashing (NOT plain text)
- Supports parent/child account hierarchy

---

### 2. Login Screen

**When NOT logged in:**
- Show company logo/branding
- Username + password input fields
- Login button
- "Forgot password?" info message
- Stop execution until authenticated

**Session State Variables:**
```python
st.session_state.logged_in = False  # Auth status
st.session_state.promoter_name = ""  # Display name
st.session_state.promoter_info = {}  # Full promoter data
```

---

### 3. Logged-In Interface

**Top Bar:**
- Welcome message with promoter name
- "Submit New Quote" button
- "My Quotes" button (view quote history)
- "Change Password" button
- "Logout" button

**Quote Submission Form:**
```
Client Details:
- Client name *
- Contact email *
- Contact phone *

Project Details:
- Project name *
- Project address *
- Upload BNG Metric (.xlsm file) *

Location Selection:
- Option A: Postcode/Address lookup (autocomplete)
- Option B: LPA + NCA dropdowns

Additional Options:
- Requote? (checkbox)
  - If yes: Enter original reference number
  - Load previous quote data
```

---

### 4. Quote Generation Process

**After form submission:**

1. **Validate inputs**
   - All required fields filled
   - Valid metric file uploaded
   - Location selected

2. **Process metric file**
   ```python
   from metric_reader import read_metric
   demand = read_metric(uploaded_file)
   ```

3. **Get location data**
   - If postcode: Query ArcGIS for LPA/NCA
   - If dropdown: Use selected values
   - Calculate neighbors using `layer_intersect_names()`

4. **Run optimization**
   ```python
   from optimizer_core import optimise, load_backend
   backend = load_backend()
   result = optimise(demand, backend, contract_size, ...)
   ```

5. **Apply promoter discount**
   - Read discount settings from promoter_info
   - Apply discount to allocation prices
   - See `EXTRACTED_PROMOTER_DISCOUNT_CODE.md`

6. **Generate outputs**
   - Client report HTML (email body)
   - PDF quote document
   - CSV allocation file
   - Store in database

7. **Send email notification**
   ```python
   from email_notification import send_email_notification
   send_email_notification(
       recipient_email=client_email,
       subject="Your BNG Quote",
       html_body=report_html,
       attachments=[pdf_file, csv_file]
   )
   ```

8. **Store submission**
   ```python
   from database import SubmissionsDB
   db = SubmissionsDB()
   db.store_submission(
       allocation_data=allocations,
       client_name=client_name,
       promoter_name=promoter_name,
       ...
   )
   ```

---

### 5. Password Management

**Change Password Feature:**
- Collapsible panel in top bar
- Form with:
  - Current password (verify with `authenticate_promoter()`)
  - New password (min 8 chars)
  - Confirm new password (must match)
- On submit:
  ```python
  db.update_introducer_password(introducer_id, new_password)
  ```
- Uses bcrypt to hash new password before storing

---

### 6. Quote History

**"My Quotes" Feature:**
- Shows all quotes submitted by this promoter
- Search by:
  - Client name
  - Reference number
  - Date range
- Display columns:
  - Reference number
  - Client name
  - Project name
  - Date submitted
  - Total cost
  - Status

**Implementation:**
```python
db = SubmissionsDB()
quotes = db.get_submissions_by_promoter(promoter_name)
# Display in table with filters
```

---

### 7. Requote Functionality

**When "This is a requote" is checked:**
1. Show field: "Original reference number"
2. On load:
   ```python
   db = SubmissionsDB()
   original = db.get_submission_by_reference(ref_number)
   ```
3. Pre-fill form with original data:
   - Client name
   - Contact details
   - Project info
   - Location (LPA/NCA)
4. User uploads NEW metric file
5. System:
   - Generates new reference with `.1`, `.2` suffix
   - Runs fresh optimization with current stock levels
   - Compares to original allocation
   - Flags any major differences

---

## Critical Differences from Office Version

### What Promoter Frontend DOES NOT Have:

❌ Metric upload for database seeding
❌ Bank management
❌ Stock management
❌ Pricing table editing
❌ Admin dashboard
❌ Direct database modification
❌ User management (except own password)

### What Promoter Frontend ONLY Does:

✅ Login authentication
✅ Submit quote requests
✅ View own quote history
✅ Download generated documents
✅ Change own password
✅ Requote existing references

---

## Database Integration

### Tables Used:

**`introducers`** - Authentication
- `id`, `name`, `username`, `password_hash`
- `discount_type`, `discount_value`
- `parent_introducer_id` (for child accounts)

**`submissions`** - Quote storage
- `reference_number`, `client_name`, `promoter_name`
- `allocation_data` (JSON), `demand_data` (JSON)
- `total_cost`, `admin_fee`, `created_at`

### Functions Needed:

```python
# From database.py
db = SubmissionsDB()
db.authenticate_introducer(username, password)
db.get_introducer_by_username(username)
db.update_introducer_password(id, new_password)
db.store_submission(...)
db.get_submissions_by_promoter(promoter_name)
db.get_submission_by_reference(ref_number)
```

---

## Security Considerations

### Password Handling:
```python
import bcrypt

# Hashing password (on registration)
password_hash = bcrypt.hashpw(
    password.encode('utf-8'), 
    bcrypt.gensalt()
).decode('utf-8')

# Verifying password (on login)
is_valid = bcrypt.checkpw(
    password.encode('utf-8'),
    stored_hash.encode('utf-8')
)
```

### Session Management:
- Use Streamlit session state
- Clear on logout
- No persistent tokens (each session is isolated)

### Data Access:
- Promoters can ONLY see their own quotes
- No access to other promoters' data
- No access to bank/stock/pricing tables

---

## UI/UX Requirements

### Branding:
- Show promoter's company name/logo
- Custom welcome message
- Branded PDF output

### User Experience:
- Clear progress indicators during optimization
- Loading messages (fun quotes about habitats)
- Error handling with helpful messages
- Success confirmation with next steps

### Mobile Responsiveness:
- Form should work on tablets
- Streamlit's default responsive layout is usually sufficient

---

## File Generation

### PDF Quote Document:
```python
from pdf_generator_promoter import generate_quote_pdf
pdf_bytes = generate_quote_pdf(
    client_name=client_name,
    project_name=project_name,
    allocations=allocations,
    promoter_name=promoter_name,
    reference_number=ref_number,
    ...
)
```

### CSV Allocation File:
```python
from sales_quotes_csv import generate_sales_quotes_csv
csv_content = generate_sales_quotes_csv(
    allocations=allocations,
    reference_number=ref_number,
    ...
)
```

### Email HTML Report:
```python
from optimizer_core import generate_client_report_table_fixed
html_body = generate_client_report_table_fixed(
    allocations=allocations,
    promoter_name=promoter_name,
    ...
)
```

---

## Environment Variables

**Required Secrets:**
```toml
[supabase]
url = "https://xxx.supabase.co"
key = "eyJxxx..."

[email]
smtp_server = "smtp.gmail.com"
smtp_port = 587
sender_email = "quotes@wildercapital.com"
sender_password = "xxx"

[arcgis]
# No auth needed for public layers
```

---

## Testing Checklist

### Authentication:
- [ ] Valid credentials log in successfully
- [ ] Invalid credentials show error
- [ ] Password change works
- [ ] Child accounts load parent discounts
- [ ] Logout clears session

### Quote Submission:
- [ ] Form validation works
- [ ] Metric file parsing works
- [ ] Location lookup works (both methods)
- [ ] Optimization runs successfully
- [ ] Discount applied correctly
- [ ] PDF generates
- [ ] CSV generates
- [ ] Email sends
- [ ] Database stores submission

### Requote:
- [ ] Original quote loads correctly
- [ ] New metric overrides old demand
- [ ] Reference number gets suffix (.1, .2)
- [ ] New allocation runs with current stock

### Security:
- [ ] Passwords are hashed (bcrypt)
- [ ] Sessions are isolated
- [ ] Promoters can't see other's quotes
- [ ] No SQL injection vulnerabilities

---

## Common Pitfalls to Avoid

### 1. **Don't store plain text passwords**
❌ `password = form_data['password']`
✅ `password_hash = bcrypt.hashpw(...)`

### 2. **Don't skip parent account lookup**
❌ Use child's name for discounts
✅ Load parent's discount settings for child accounts

### 3. **Don't use same session for all promoters**
❌ Global variables for promoter info
✅ Use `st.session_state` per session

### 4. **Don't let promoters access admin features**
❌ Show all database operations
✅ Restrict to quote submission only

### 5. **Don't forget to clear session on logout**
❌ Leave `logged_in = True`
✅ Reset all session state variables

---

## Summary

Build a **login-protected quote submission interface** that:
1. Authenticates promoters against `introducers` table
2. Presents a simple form for client/project details
3. Processes BNG metric files
4. Runs optimization with location-based pricing
5. Applies promoter discounts automatically
6. Generates PDF/CSV/Email outputs
7. Stores submissions in database
8. Allows viewing quote history
9. Supports requoting with reference numbers
10. Provides password management

**Key principle:** Promoters are **submitting requests** for quotes, not generating them directly in the UI like the office version. The system does the heavy lifting in the background.
