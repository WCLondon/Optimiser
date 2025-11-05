# Promoter Quote System - Final Implementation Summary

## ✅ Implementation Complete - Streamlit Version with Login

### What Was Built

A **single Streamlit application** that serves as a quote request system for all promoters with:

1. **Login Authentication**
   - Username: Promoter name from database
   - Password: Promoter name + "1" (e.g., EPT → EPT1)
   - Session-based authentication
   - Logout capability

2. **Quote Request Form**
   - Modern, responsive UI
   - File upload for BNG metrics
   - Form validation
   - Auto-quote vs manual review logic
   - Database persistence with promoter tracking

3. **Database Integration**
   - Loads promoters from `customer_promoters` table
   - Saves submissions to `submissions` table
   - Tracks which promoter submitted each quote

## Quick Start

```bash
# Start the app
./run_promoter_app.sh

# Or manually
streamlit run promoter_app.py --server.port 8502

# Access at http://localhost:8502
```

## Login Credentials

| Username | Password | Description |
|----------|----------|-------------|
| EPT      | EPT1     | Environmental Planning & Testing |
| Arbtech  | Arbtech1 | Arbtech |
| *Any promoter in DB* | *Name+1* | Loaded from customer_promoters table |

## User Flow

```
1. User visits http://localhost:8502
   ↓
2. Login page displayed
   - Shows available promoters
   - Enter username (promoter name)
   - Enter password (name + 1)
   ↓
3. Authentication check
   - Success → Show quote form
   - Fail → Show error with hint
   ↓
4. Quote form (authenticated)
   - Promoter badge shows who's logged in
   - Fill contact email
   - Enter site location (address/postcode)
   - Upload BNG metric file (.xlsx)
   - Add optional notes
   - Check consent
   - Submit
   ↓
5. Processing
   - Read metric file
   - Calculate quote total
   - Save to database with promoter_name
   - Apply threshold logic
   ↓
6. Result
   - If < £20k: Show PDF download (placeholder)
   - If ≥ £20k: Show "team will contact you"
   - Option to submit another quote
```

## Files Structure

```
Optimiser/
├── promoter_app.py              # Main Streamlit app with login
├── run_promoter_app.sh          # Launcher script
├── STREAMLIT_PROMOTER_GUIDE.md  # Complete documentation
├── metric_reader.py             # Existing - reads BNG metrics
├── repo.py                      # Existing - database access
└── database.py                  # Existing - submissions DB
```

## Key Features

### 1. Login System

**Authentication Logic:**
```python
def authenticate(username, password):
    promoters = get_promoters()  # From database
    for promoter in promoters:
        if promoter['name'].upper() == username.upper():
            expected_password = promoter['name'] + "1"
            if password == expected_password:
                return True
    return False
```

**Session Management:**
- `st.session_state.authenticated` - Login status
- `st.session_state.promoter_name` - Current user
- Logout clears session and redirects to login

### 2. Database Integration

**Promoters Loaded From:**
```sql
SELECT DISTINCT 
    promoter_name,
    promoter_discount_type,
    promoter_discount_value
FROM customer_promoters 
WHERE promoter_name IS NOT NULL 
ORDER BY promoter_name
```

**Submissions Saved With:**
- All standard fields from existing SubmissionsDB
- `promoter_name` = logged-in promoter
- `client_name` = from email
- `total_cost` = calculated quote
- Full metric data in `allocation_results`

### 3. Quote Processing

**Simplified for Now:**
- Reads metric using `metric_reader.py`
- Calculates units (area + hedgerow + watercourse)
- Simple pricing: units × £10,000
- Real optimizer integration TODO

**Threshold Logic:**
```python
auto_quoted = quote_total < 20000.0

if auto_quoted:
    # Generate PDF (placeholder for now)
    # Return download
else:
    # Show thank you message
    # Send email (TODO)
```

## Deployment

### Local Development

```bash
./run_promoter_app.sh
```

### Production Options

**Option 1: Streamlit Cloud**
- Deploy directly from GitHub
- Get URL: `promoters.streamlit.app`
- Share with all promoters

**Option 2: Self-Hosted**
```bash
# Systemd service
sudo systemctl start bng-promoter-app

# Access at configured domain
https://promoters.bng-quotes.wildcapital.co.uk
```

**Option 3: Docker**
```bash
docker build -t bng-promoter-app .
docker run -p 8502:8501 bng-promoter-app
```

## Testing

### Test Login

1. Start app: `./run_promoter_app.sh`
2. Visit: http://localhost:8502
3. Login with:
   - Username: `EPT`
   - Password: `EPT1`
4. Verify: Form appears with "EPT" badge

### Test Invalid Login

1. Try:
   - Username: `WrongName`
   - Password: `wrong`
2. Verify: Error message with password hint

### Test Submission

1. After login, fill form:
   - Email: test@example.com
   - Postcode: SW1A 1AA
   - Upload: BNG metric .xlsx
   - Check consent
2. Submit
3. Verify: Success message appears
4. Check database:
   ```sql
   SELECT * FROM submissions 
   WHERE promoter_name = 'EPT' 
   ORDER BY submission_date DESC LIMIT 1;
   ```

### Test Logout

1. Click "🚪 Logout" in sidebar
2. Verify: Returns to login page
3. Verify: Session cleared

## Adding New Promoters

### Add to Database

```sql
INSERT INTO customer_promoters (
    customer_name, 
    company_name, 
    promoter_name
) VALUES (
    'New Client',
    'New Company', 
    'NewPromoter'
);
```

Login:
- Username: `NewPromoter`
- Password: `NewPromoter1`

## Security Considerations

### Current (Development)

⚠️ **Simple password**: Name + "1" is easy to guess  
✅ **Database-driven**: Users from database  
✅ **Session management**: Streamlit handles it  
✅ **Logout**: Users can end session  

### Recommended for Production

1. **Hash passwords** in database
2. **Rate limit** login attempts
3. **Session timeout** after inactivity
4. **HTTPS only** (no plain HTTP)
5. **Audit logging** of logins
6. **Password reset** capability

## Monitoring

### Track by Promoter

```sql
-- Submissions per promoter
SELECT 
    promoter_name,
    COUNT(*) as total,
    AVG(total_cost) as avg_quote,
    SUM(total_cost) as total_value
FROM submissions
WHERE promoter_name IS NOT NULL
GROUP BY promoter_name
ORDER BY total DESC;

-- Recent activity
SELECT 
    promoter_name,
    submission_date,
    client_name,
    total_cost,
    site_location
FROM submissions
WHERE promoter_name IS NOT NULL
ORDER BY submission_date DESC
LIMIT 20;
```

## Advantages

### vs. Multiple Apps

✅ **Single deployment** - One app for all  
✅ **Centralized updates** - Update once  
✅ **Lower resources** - One instance  
✅ **Easier maintenance** - Single codebase  

### vs. FastAPI Backend

✅ **Faster to test** - No backend deployment  
✅ **Familiar tools** - Streamlit environment  
✅ **Shared code** - Uses existing modules  
✅ **Quick iteration** - Change and test immediately  

### vs. Public Form

✅ **Authentication** - Know who's using it  
✅ **Tracking** - Promoter tagged on submissions  
✅ **Accountability** - Audit trail  
✅ **Control** - Can disable promoters  

## Next Steps

### Short Term (Testing)

- [ ] Test with live database connection
- [ ] Verify promoter loading from customer_promoters
- [ ] Test full submission flow
- [ ] Verify promoter tracking in submissions

### Medium Term (Enhancement)

- [ ] Implement actual PDF generation (ReportLab)
- [ ] Add email notifications for manual reviews
- [ ] Integrate full optimizer (not simplified version)
- [ ] Add location resolution (LPA/NCA from postcode)
- [ ] Store uploaded files in Supabase Storage

### Long Term (Production)

- [ ] Enhanced password security (hashing)
- [ ] Session timeout
- [ ] Rate limiting
- [ ] Admin dashboard for viewing all submissions
- [ ] Analytics and reporting
- [ ] Per-promoter branding/configuration

## Alternatives Available

The FastAPI backend implementation also exists in `backend/` directory if:
- Need better performance at scale
- Want custom URLs (`/EPT` instead of login)
- Need more control over caching
- Require complex workflows

## Support

For issues:
1. Check terminal output for errors
2. Verify database connection: `.streamlit/secrets.toml`
3. Test with sample login (EPT/EPT1)
4. Check promoter query in database
5. Review Streamlit logs

## Summary

✅ **Single Streamlit app** for all promoters  
✅ **Login authentication** with database-driven users  
✅ **Quote submission** with tracking by promoter  
✅ **Simple deployment** - one instance serves all  
✅ **Ready for testing** with provided credentials  

**Status: COMPLETE and READY FOR TESTING** 🚀

---

**To Get Started:**
```bash
./run_promoter_app.sh
# Visit http://localhost:8502
# Login: EPT / EPT1
```
