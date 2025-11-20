# QuickOpt App - Internal BNG Quote Request Tool

## Overview

`quickopt_app.py` is an internal version of the promoter app designed specifically for office use by the WCLondon team. It provides a streamlined interface for submitting BNG quote requests without the restrictions applied to external promoters.

## Key Features

### 1. Internal Authentication
- **Username:** WC0323
- **Password:** Wimborne (same as main app.py)
- Hardcoded credentials for internal team access
- No database lookup required

### 2. No Quote Threshold
Unlike the promoter app which has a £50,000 threshold:
- **All quotes** are sent for review regardless of amount
- No automatic PDF download for any quotes
- All quotes go through the review team for approval

### 3. Email Behavior
- All submissions send a `full_quote` email to reviewers
- Includes complete quote details in email
- Attaches metric file and CSV allocation data
- No differentiation based on quote amount

## Differences from promoter_app.py

| Feature | promoter_app.py | quickopt_app.py |
|---------|----------------|----------------|
| Authentication | Database lookup of promoters | Hardcoded WC0323 credentials |
| £50k Threshold | Yes (different handling) | No (all go to review) |
| PDF Download | Yes (for quotes < £50k) | No (all via email review) |
| Email Type | Quote notification or full quote | Always full quote |
| Target Users | External promoters/introducers | Internal office team |
| Branding | Promoter-focused | Internal-focused |

## Usage

### Running the App

```bash
streamlit run quickopt_app.py
```

### Login
1. Navigate to the app URL
2. Enter username: `WC0323`
3. Enter password: `Wimborne`
4. Click "Login"

### Submitting a Quote
1. Fill in client details (optional fields supported)
2. Provide site location (address/postcode OR LPA/NCA)
3. Upload BNG Metric file (xlsx, xlsm, or xlsb)
4. Add any notes (optional)
5. Check the consent checkbox
6. Click "Submit Quote Request"

### After Submission
- All quotes are marked as "Under Review"
- Full quote email sent to review team
- No PDF download available
- Can submit another quote immediately

## Technical Details

### Key Code Changes
- Authentication function simplified to check hardcoded credentials
- Removed all £50,000 threshold checks
- Email sending always uses `email_type='full_quote'`
- PDF generation code removed (not needed for internal use)
- UI updated to reflect internal branding

### Security
- Same security as main app.py for WC0323 user
- Credentials match production defaults
- No additional security vulnerabilities introduced
- CodeQL analysis passed with 0 alerts

## Maintenance

When updating this file:
1. Keep in sync with promoter_app.py for core functionality
2. Maintain the key differences (auth, threshold, email)
3. Test authentication logic after changes
4. Ensure all quotes still go to review

## Files
- **Main file:** `quickopt_app.py`
- **Based on:** `promoter_app.py`
- **Created:** 2025-11-20

## Support
For issues or questions about QuickOpt, contact the development team or refer to the main app.py documentation.
