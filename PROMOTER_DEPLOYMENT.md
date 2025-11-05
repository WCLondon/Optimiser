# Promoter App Deployment Guide

This guide explains how to deploy the Promoter Quote Form (`promoter_app.py`) separately from the main BNG Optimizer (`app.py`).

## The Two Apps

This repository contains **two different Streamlit applications**:

1. **Main BNG Optimizer** (`app.py`) - Full-featured optimizer with interactive UI
2. **Promoter Quote Form** (`promoter_app.py`) - Simple login-based quote submission system

## Deploying on Streamlit Cloud

When deploying on Streamlit Cloud, you need to specify which app to run.

### Step-by-Step Instructions

1. **Create a new app** on Streamlit Cloud (or edit existing)

2. **In the app settings**, find the **"Main file path"** field

3. **Set the main file to:**
   ```
   promoter_app.py
   ```
   
   (NOT `app.py`)

4. **Configure secrets** in the Streamlit Cloud dashboard:
   - Go to Settings → Secrets
   - Add your database connection string and SMTP credentials (see below)

5. **Deploy or redeploy** the app

### Required Secrets for Streamlit Cloud

Add these to your Streamlit Cloud secrets (Settings → Secrets):

```toml
# Database connection
DB_URL = "postgresql://user:password@host:port/database"

# SMTP Configuration for email notifications
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = "587"
SMTP_USER = "your-email@gmail.com"
SMTP_PASSWORD = "your-app-password"
SMTP_FROM_EMAIL = "quotes@wildcapital.co.uk"
SMTP_FROM_NAME = "Wild Capital BNG Quotes"

# Reviewer emails (comma-separated)
REVIEWER_EMAILS = "reviewer1@wildcapital.co.uk,reviewer2@wildcapital.co.uk"
```

## Deploying Locally

To run the promoter app locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the promoter app
streamlit run promoter_app.py --server.port 8502
```

Or use the provided script:

```bash
./run_promoter_app.sh
```

## Deploying Both Apps

If you want to deploy **both** apps (main optimizer and promoter form):

### Option 1: Two Separate Streamlit Cloud Apps

1. **Deploy first app** (Main Optimizer):
   - Main file path: `app.py`
   - URL: `https://yourapp-main.streamlit.app`

2. **Deploy second app** (Promoter Form):
   - Main file path: `promoter_app.py`
   - URL: `https://yourapp-promoter.streamlit.app`

### Option 2: Multi-page App

Create a landing page that routes to either app based on user type:

```python
# pages/1_Main_Optimizer.py
# pages/2_Promoter_Form.py
```

## Verifying the Correct App is Running

**Main Optimizer (`app.py`):**
- Title: "BNG Optimiser"
- Shows username/password login for internal users
- Has complex forms with LPA/NCA selection
- Shows interactive maps and optimization results

**Promoter Form (`promoter_app.py`):**
- Title: "BNG Quote Request"
- Shows simple login with introducer names from database
- Single-page form with file upload
- Auto-quote threshold logic (£20k)

## Troubleshooting

### "Wrong app is loading"

**Problem:** Streamlit Cloud is running `app.py` instead of `promoter_app.py`

**Solution:** Change "Main file path" in Streamlit Cloud settings to `promoter_app.py`

### "ModuleNotFoundError: No module named 'reportlab'"

**Problem:** PDF generation requires reportlab library

**Solution:** 
- Streamlit Cloud automatically installs from `requirements.txt` (already includes reportlab)
- For local deployment: `pip install reportlab>=4.0`

### "Database connection error"

**Problem:** Database credentials not configured

**Solution:** Add `DB_URL` to secrets (see "Required Secrets" section above)

### "Email not sending"

**Problem:** SMTP credentials not configured

**Solution:** Add SMTP settings to secrets (see "Required Secrets" section above)

## Production Checklist

Before deploying to production:

- [ ] Main file path set to `promoter_app.py`
- [ ] Database URL configured in secrets
- [ ] SMTP credentials configured in secrets
- [ ] Reviewer emails configured
- [ ] Password column added to `introducers` table
- [ ] Passwords set for all introducers in database
- [ ] Test login with real introducer credentials
- [ ] Test file upload and quote generation
- [ ] Test email notifications
- [ ] Test PDF download (for auto-quotes < £20k)

## Support

For deployment issues:
1. Check the app logs in Streamlit Cloud dashboard
2. Verify all secrets are properly configured
3. Ensure database has `introducers` table with `password` column
4. Check that SMTP credentials are valid

## URLs

Once deployed, your promoter form will be accessible at:
- Streamlit Cloud: `https://your-app-name.streamlit.app`
- Local: `http://localhost:8502`

Users will see a login page where they enter their introducer name and password from the database.
