# BNG Optimiser - Standalone

A Streamlit application for optimizing Biodiversity Net Gain (BNG) unit allocation across multiple habitat banks.

## Features

### Core Functionality
- **Location-based Optimization**: Find optimal BNG unit allocations based on target site location (LPA/NCA)
- **Multi-bank Support**: Search across multiple habitat banks for best pricing and availability
- **Habitat Matching**: Intelligent matching of demand and supply habitats following trading rules
- **Pricing Tiers**: Automatic tier calculation (local/adjacent/far) based on geographic proximity
- **Manual Entries**: Add hedgerow and watercourse units manually to supplement optimization results
- **Client Reports**: Generate professional client-facing reports and email templates

### Database & Admin Features (NEW)
- **Automatic Data Tracking**: All submissions and optimization results saved automatically
- **Admin Dashboard**: Secure password-protected dashboard for viewing historical data
- **Advanced Filtering**: Filter submissions by date, client, LPA, NCA, or reference number
- **Data Export**: Export submissions and allocation details to CSV
- **Summary Statistics**: View total submissions, revenue, and top clients/LPAs

See [DATABASE_FEATURE.md](DATABASE_FEATURE.md) for complete database documentation.

## Requirements

- Python 3.8+
- Streamlit 1.37+
- See `requirements.txt` for full dependencies

## Installation

1. Clone the repository:
```bash
git clone https://github.com/WCLondon/Optimiser.git
cd Optimiser
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Configure authentication:
Create `.streamlit/secrets.toml`:
```toml
[auth]
username = "your_username"
password = "your_password"

[admin]
password = "admin_password"
```

## Usage

### Running the Application

```bash
streamlit run app.py
```

The app will open in your default web browser at `http://localhost:8501`

### Basic Workflow

1. **Login**: Use your credentials (default: WC0323 / Wimborne)

2. **Load Backend**: Upload or use the example backend Excel file containing:
   - Banks data
   - Pricing information
   - Habitat catalog
   - Stock availability
   - Trading rules

3. **Locate Site**: Enter postcode or address to determine target LPA/NCA

4. **Enter Demand**: Add habitat units needed for your development

5. **Optimize**: Run the optimizer to find best allocation across banks

6. **Review Results**: View allocation details, costs, and selected banks

7. **Generate Report**: Create client-facing report with email template

8. **Automatic Save**: Submission automatically saved to database when generating report

### Admin Dashboard

1. Switch to "Admin Dashboard" mode in the sidebar
2. Enter admin password (default: WCAdmin2024)
3. View, filter, and export historical submissions
4. Access detailed allocation breakdowns

## Project Structure

```
Optimiser/
├── app.py                          # Main Streamlit application
├── database.py                     # Database module for submissions tracking
├── requirements.txt                # Python dependencies
├── submissions.db                  # SQLite database (created automatically)
├── .gitignore                      # Git ignore rules
├── data/                           # Example backend data
│   └── HabitatBackend_WITH_STOCK.xlsx
└── docs/
    ├── DATABASE_FEATURE.md         # Database feature documentation
    ├── MANUAL_ENTRIES_FEATURE.md   # Manual entries documentation
    ├── IMPLEMENTATION_SUMMARY.md   # Implementation details
    ├── PAIRED_ALLOCATION_FIX.md    # Paired allocation documentation
    └── UI_MOCKUP.md                # UI design reference
```

## Key Features Explained

### Location-Based Tiers
- **Local**: Target site within same LPA or NCA as bank
- **Adjacent**: Target site in neighboring LPA/NCA
- **Far**: All other locations

Tiers affect unit multipliers and pricing.

### Paired Allocations
Some habitats (e.g., Orchard) use "paired" allocations combining:
- Primary habitat (e.g., Orchard)
- Secondary habitat (cheapest eligible area habitat)

Mixing ratios and pricing calculated automatically.

### Stock Management
- Real-time stock tracking
- Quote reservation options
- Automatic availability checking

### Manual Additions
After optimization, you can manually add:
- Hedgerow units
- Watercourse units

These integrate seamlessly into final reports and costs.

## Configuration

### Backend Data Format
The backend Excel file must contain these sheets:
- **Banks**: Bank details (name, location, coordinates)
- **Pricing**: Price per unit by bank, habitat, tier, contract size
- **HabitatCatalog**: Habitat definitions and trading rules
- **Stock**: Available units per bank and habitat
- **DistinctivenessLevels**: Distinctiveness categories
- **SRM**: Strategic Resource Multipliers
- **TradingRules** (optional): Custom trading rules

### Optimization Modes
- **PuLP Solver** (if installed): Optimal mathematical solution
- **Greedy Algorithm** (fallback): Fast heuristic solution

## Security Notes

- Default passwords should be changed in production
- Database file (`submissions.db`) excluded from git
- Admin dashboard requires separate authentication
- No sensitive data exposed in client-facing reports

## Troubleshooting

### Common Issues

**"No backend loaded"**
- Upload a valid backend Excel file or enable "Use example backend"

**"No pricing rows found"**
- Check that Pricing sheet has data for selected contract size
- Verify habitat names match between demand and catalog

**"Optimization failed"**
- Check stock availability
- Verify trading rules allow requested allocations
- Review diagnostics section for details

**"Database not saving"**
- Ensure write permissions in application directory
- Check that optimization completed successfully
- Verify client details filled in before clicking "Update Email Details"

### Getting Help

- Check the relevant documentation files in the project
- Review the diagnostics section in the app
- Check Streamlit logs for detailed error messages

## License

[Add your license information here]

## Contact

Wild Capital - [contact information]

## Version History

### v9.14 (Current)
- Added database tracking for all submissions
- Implemented secure admin dashboard
- Added data export functionality
- Enhanced filtering and search capabilities

### v9.13
- Added "Start New Quote" functionality
- Improved map refresh behavior
- Enhanced state management

### v9.12
- Fixed map display issues
- Improved UI responsiveness
- Enhanced error handling

See git history for complete changelog.
