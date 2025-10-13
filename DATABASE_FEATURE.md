# Database Feature Documentation

## Overview
The BNG Optimiser now includes a comprehensive database system for tracking all form submissions and optimization results. This feature provides secure storage and retrieval of historical data through an admin dashboard.

## Features

### 1. Automatic Data Storage
- **What is stored:**
  - Client details (name, reference number, site location)
  - Location metadata (LPA, NCA, coordinates, neighbors)
  - All form inputs and demand habitats
  - Complete allocation results (banks used, units, prices, costs)
  - Manual hedgerow and watercourse entries
  - Optimization metadata (contract size, total cost, admin fee)
  - Username of person who created the submission

- **When data is saved:**
  - Automatically when the "Update Email Details" form is submitted in the client report section
  - Only submissions with completed optimizations are saved

### 2. Admin Dashboard
Access the admin dashboard by:
1. Click "Admin Dashboard" in the sidebar mode selector
2. Enter the admin password (default: `WCAdmin2024`, can be configured in Streamlit secrets)
3. View and manage all historical submissions

### 3. Dashboard Features

#### Summary Statistics
- Total number of submissions
- Total revenue (with admin fees)
- Top LPAs by submission count
- Top clients by submission count

#### Filtering & Search
Filter submissions by:
- Date range (start/end dates)
- Client name (partial match)
- LPA (partial match)
- NCA (partial match)
- Reference number (partial match)

#### Data Export
- Export filtered submissions to CSV
- Export allocation details for specific submissions
- Timestamped filenames for easy tracking

#### Detailed View
- View full details of any submission
- See complete allocation breakdown
- Export allocation details to CSV

## Technical Details

### Database Technology
- **SQLite** - Local file-based database (`submissions.db`)
- No external dependencies or cloud services required
- Suitable for single-user or small team deployments

### Database Schema

#### submissions table
- `id` - Primary key
- `submission_date` - ISO format timestamp
- `client_name`, `reference_number`, `site_location` - Client info
- `target_lpa`, `target_nca`, `target_lat`, `target_lon` - Location
- `lpa_neighbors`, `nca_neighbors` - JSON arrays
- `demand_habitats` - JSON array of demand rows
- `contract_size`, `total_cost`, `admin_fee`, `total_with_admin` - Financial
- `num_banks_selected`, `banks_used` - Bank information
- `manual_hedgerow_entries`, `manual_watercourse_entries` - JSON arrays
- `allocation_results` - Full allocation DataFrame as JSON
- `username` - User who created the submission

#### allocation_details table
- `id` - Primary key
- `submission_id` - Foreign key to submissions
- `bank_key`, `bank_name` - Bank identification
- `demand_habitat`, `supply_habitat` - Habitat matching
- `allocation_type`, `tier` - Allocation specifics
- `units_supplied`, `unit_price`, `cost` - Financial details

### Security

#### Password Protection
- Admin dashboard requires separate password authentication
- Password can be configured via Streamlit secrets:
  ```toml
  # .streamlit/secrets.toml
  [admin]
  password = "YourSecurePassword"
  ```
- Default password: `WCAdmin2024` (change in production!)

#### Data Privacy
- Database file excluded from git via `.gitignore`
- No sensitive data exposed to non-admin users
- Admin session locks after mode switch or logout

## Configuration

### Using Streamlit Secrets
Create a `.streamlit/secrets.toml` file:

```toml
[auth]
username = "WC0323"
password = "Wimborne"

[admin]
password = "YourSecureAdminPassword"
```

### Custom Database Location
The database can be configured in `database.py`:
```python
# Change the default path
db = SubmissionsDB(db_path="custom_path/submissions.db")
```

### For Multi-User Environments
For multiple concurrent users or remote access:
- Consider using PostgreSQL instead of SQLite
- Update `database.py` to use `psycopg2` or SQLAlchemy
- Configure database connection string in Streamlit secrets

## Usage Workflow

### For Regular Users (Optimiser Mode)
1. Complete optimization as usual
2. Generate client report and enter client details
3. Click "Update Email Details" - submission is automatically saved
4. Success message confirms database storage

### For Administrators
1. Switch to "Admin Dashboard" in sidebar
2. Enter admin password
3. View summary statistics
4. Use filters to find specific submissions
5. Export data as needed
6. View detailed allocation breakdowns

## Maintenance

### Database Backup
Regularly backup the `submissions.db` file:
```bash
cp submissions.db submissions_backup_$(date +%Y%m%d).db
```

### Database Size Management
- Monitor database file size
- Consider archiving old submissions
- Export historical data to CSV and remove from database if needed

### Troubleshooting

#### Database initialization errors
- Check file permissions on `submissions.db`
- Ensure write access to application directory
- Check logs for specific error messages

#### Data not saving
- Verify optimization completed successfully
- Check client details are filled in
- Look for error messages in the UI
- Check application logs

#### Admin password not working
- Verify `.streamlit/secrets.toml` configuration
- Check for typos in password
- Restart Streamlit app after changing secrets

## Future Enhancements

Potential improvements for the future:
- Bulk delete/archive functionality
- Advanced analytics and reporting
- Integration with external CRM systems
- Automated email notifications
- Data visualization dashboards
- API endpoints for programmatic access

## Migration Guide

### From No Database to Database Version
1. Pull the latest code with database feature
2. Install any new dependencies (none required for SQLite)
3. Run the app - database will be created automatically
4. Existing work is not retroactively added
5. New submissions will be tracked going forward

### To PostgreSQL (Future)
1. Export existing data to CSV
2. Update `database.py` with PostgreSQL connection
3. Create tables in PostgreSQL
4. Import CSV data
5. Update connection string in app configuration
