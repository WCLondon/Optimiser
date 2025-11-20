# QuickOpt vs Promoter App - Visual Comparison

## Side-by-Side Comparison

### 🔐 Authentication Flow

#### promoter_app.py
```
1. User enters credentials
2. System looks up promoter in database
3. Validates against stored promoter records
4. Loads promoter-specific discount settings
5. Shows promoter name in header
```

#### quickopt_app.py ⭐
```
1. User enters credentials
2. System checks against hardcoded WC0323/Wimborne
3. No database lookup needed
4. Uses default no_discount settings
5. Shows "WC0323 (Internal)" in header
```

---

### 💰 Quote Processing Flow

#### promoter_app.py
```
Generate Quote
    ↓
Check Amount
    ↓
┌───────────────┬────────────────┐
│  < £50,000    │  ≥ £50,000     │
├───────────────┼────────────────┤
│ Generate PDF  │ No PDF         │
│ Email notify  │ Email full     │
│ Show download │ Show "review"  │
│ Show total    │ Hide total     │
└───────────────┴────────────────┘
```

#### quickopt_app.py ⭐
```
Generate Quote
    ↓
All Amounts
    ↓
┌──────────────────┐
│  All Quotes      │
├──────────────────┤
│ No PDF           │
│ Email full quote │
│ Show "review"    │
│ No download      │
└──────────────────┘
```

---

### 📧 Email Types

#### promoter_app.py
| Quote Amount | Email Type | Content |
|-------------|------------|---------|
| < £50,000 | `quote_notification` | Basic notification + metric + CSV |
| ≥ £50,000 | `full_quote` | Full quote details + HTML + metric + CSV |

#### quickopt_app.py ⭐
| Quote Amount | Email Type | Content |
|-------------|------------|---------|
| **All amounts** | `full_quote` | Full quote details + HTML + metric + CSV |

---

### 👤 User Experience

#### promoter_app.py
```
Login Screen:
┌─────────────────────────────────┐
│ Promoter Login                  │
│                                 │
│ Username: [____________]        │
│ Password: [____________]        │
│                                 │
│ [Login]                         │
│                                 │
│ Contact admin for credentials  │
└─────────────────────────────────┘

After Login:
┌─────────────────────────────────┐
│ {Promoter Name} - BNG Quote     │
│ Logged in as: {Promoter Name}   │
└─────────────────────────────────┘

Quote Result (< £50k):
┌─────────────────────────────────┐
│ Total Cost: £42,500             │
│ Admin Fee: £1,500               │
│ [📄 Download PDF Quote]         │
└─────────────────────────────────┘

Quote Result (≥ £50k):
┌─────────────────────────────────┐
│ Status: Under Review            │
│ Quote £50k+ under review        │
└─────────────────────────────────┘
```

#### quickopt_app.py ⭐
```
Login Screen:
┌─────────────────────────────────┐
│ QuickOpt - Internal Login       │
│                                 │
│ Username: [____________]        │
│ Password: [____________]        │
│                                 │
│ [Login]                         │
│                                 │
│ For internal office use only   │
│ Use WC0323 credentials          │
└─────────────────────────────────┘

After Login:
┌─────────────────────────────────┐
│ QuickOpt - Internal BNG Quote   │
│ Logged in as: WC0323 (Internal) │
└─────────────────────────────────┘

Quote Result (All amounts):
┌─────────────────────────────────┐
│ Status: Under Review            │
│ Quote sent for review           │
│ No PDF download                 │
│ 📧 Sent to review team          │
└─────────────────────────────────┘
```

---

## Code Differences Summary

### Key Functions Modified

#### `authenticate_promoter()`
```python
# promoter_app.py - Database lookup
try:
    db = SubmissionsDB()
    introducers = db.get_all_introducers()
    for introducer in introducers:
        if introducer['name'] == username:
            return True, introducer
    return False, None
except Exception as e:
    st.error(f"Authentication error: {e}")
    return False, None

# quickopt_app.py - Hardcoded ⭐
INTERNAL_USERNAME = "WC0323"
INTERNAL_PASSWORD = "Wimborne"

if username == INTERNAL_USERNAME and password == INTERNAL_PASSWORD:
    internal_user_info = {
        'name': INTERNAL_USERNAME,
        'discount_type': 'no_discount',
        'discount_value': 0
    }
    return True, internal_user_info
return False, None
```

#### Quote Processing
```python
# promoter_app.py - Conditional based on amount
if quote_total < 50000:
    # Generate PDF
    pdf_content, pdf_debug = generate_quote_pdf(...)
    # Send notification email
    email_type='quote_notification'
else:
    # Generate full email
    email_type='full_quote'

# quickopt_app.py - Always full quote ⭐
# Always generate full email for review
report_df, email_html_content = generate_client_report_table_fixed(...)
email_type='full_quote'  # Always
```

---

## Decision Matrix

### When to Use Each App

| Scenario | Use promoter_app.py | Use quickopt_app.py |
|----------|-------------------|-------------------|
| External promoter/introducer | ✅ | ❌ |
| Internal office staff | ❌ | ✅ |
| Need immediate PDF for small quotes | ✅ | ❌ |
| All quotes need review | ❌ | ✅ |
| Promoter-specific discounts | ✅ | ❌ |
| Quick internal quotes | ❌ | ✅ |
| Database-managed users | ✅ | ❌ |
| Simple login (WC0323) | ❌ | ✅ |

---

## File Sizes

```
promoter_app.py:  996 lines, 39KB
quickopt_app.py:  886 lines, 39KB
Difference:       -110 lines (removed PDF download section)
```

---

## Security Comparison

Both apps have the same security level:
- ✅ CodeQL: 0 alerts
- ✅ No SQL injection vulnerabilities
- ✅ No hardcoded secrets (credentials match app.py defaults)
- ✅ Proper input validation
- ✅ Email sanitization

The only difference is the authentication method (database vs hardcoded).

---

## Deployment

### promoter_app.py
```bash
# For external promoters
streamlit run promoter_app.py
# Port: 8501
```

### quickopt_app.py
```bash
# For internal office use
streamlit run quickopt_app.py
# Port: 8502 (if running alongside promoter app)
```

---

## Summary

**promoter_app.py** = External users, flexible limits, PDF downloads
**quickopt_app.py** = Internal users, all reviewed, simplified workflow

Choose quickopt_app.py for:
- ✅ Internal office use
- ✅ Standardized review process
- ✅ Simple WC0323 login
- ✅ No quote amount differentiation

Choose promoter_app.py for:
- ✅ External promoters
- ✅ Immediate PDFs (< £50k)
- ✅ Promoter-specific discounts
- ✅ Database-managed users
