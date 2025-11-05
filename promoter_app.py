"""
Streamlit Promoter Quote Form with Login
Single app for all promoters - login determines which promoter's submissions are tracked
Username: Promoter name from database
Password: From password column in introducers table
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from io import BytesIO
from typing import Optional, Dict, List
import sys
import os

# Set flag to prevent app.py from running its UI when imported
os.environ['IMPORTING_FROM_PROMOTER_APP'] = '1'

# Import existing modules
import metric_reader
import repo
from database import SubmissionsDB
from email_notification import send_manual_review_email

# Try to import the report generation function from app.py
try:
    from app import generate_client_report_table_fixed
    HAS_CLIENT_REPORT_FUNCTION = True
except Exception as e:
    HAS_CLIENT_REPORT_FUNCTION = False
    print(f"Warning: Could not import generate_client_report_table_fixed from app.py: {e}")
    print("PDF generation will use simplified format.")

# Try to import PDF generator (requires reportlab)
try:
    from pdf_generator_promoter import generate_quote_pdf
    PDF_GENERATION_AVAILABLE = True
except ImportError as e:
    PDF_GENERATION_AVAILABLE = False
    print(f"Warning: PDF generation not available - {e}")
    print("Install reportlab to enable PDF generation: pip install reportlab>=4.0")

# Configure page
st.set_page_config(
    page_title="BNG Quote Request",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Constants
AUTO_QUOTE_THRESHOLD = 20000.0  # £20,000
MAX_FILE_SIZE_MB = 15

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'promoter_name' not in st.session_state:
    st.session_state.promoter_name = None
if 'submission_complete' not in st.session_state:
    st.session_state.submission_complete = False
if 'submission_result' not in st.session_state:
    st.session_state.submission_result = None


def get_promoters() -> List[Dict]:
    """
    Load promoters from database
    Returns list of promoter dictionaries with name, password, discount info, etc.
    """
    try:
        # Fetch promoters from introducers table
        engine = repo.get_db_engine()
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("""
                SELECT DISTINCT 
                    name,
                    password,
                    discount_type,
                    discount_value
                FROM introducers 
                WHERE name IS NOT NULL 
                AND name != ''
                ORDER BY name
            """))
            
            promoters = []
            for row in result:
                promoters.append({
                    'name': row[0],
                    'password': row[1] if row[1] else row[0] + '1',  # Fallback to name+1 if no password
                    'discount_type': row[2],
                    'discount_value': row[3]
                })
            
            return promoters
    except Exception as e:
        st.error(f"Error loading promoters: {str(e)}")
        # Return some default promoters for testing
        return [
            {'name': 'ETP', 'password': 'ETP1', 'discount_type': None, 'discount_value': None},
            {'name': 'Arbtech', 'password': 'Arbtech1', 'discount_type': None, 'discount_value': None},
            {'name': 'Cypher', 'password': 'Cypher1', 'discount_type': None, 'discount_value': None}
        ]


def authenticate(username: str, password: str) -> bool:
    """
    Authenticate promoter
    Username: Promoter name (case-insensitive)
    Password: From database password column
    """
    promoters = get_promoters()
    
    # Check if username exists (case-insensitive)
    for promoter in promoters:
        if promoter['name'].upper() == username.upper():
            # Check password from database
            if password == promoter['password']:
                return True
    
    return False


def show_login_page():
    """Display login page"""
    st.markdown("""
    <div class="promoter-header">
        <div class="form-title">BNG Quote System</div>
        <div class="form-subtitle">Promoter Login</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Get available promoters
    promoters = get_promoters()
    promoter_names = [p['name'] for p in promoters]
    
    st.info(f"📋 Available promoters: {', '.join(promoter_names)}")
    
    with st.form("login_form"):
        st.subheader("Login")
        
        username = st.text_input(
            "Username",
            placeholder="Enter promoter name",
            help="Your promoter name (e.g., ETP, Arbtech)"
        )
        
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter password",
            help="Your promoter password"
        )
        
        submit = st.form_submit_button("🔐 Login", use_container_width=True)
        
        if submit:
            if not username or not password:
                st.error("Please enter both username and password")
            elif authenticate(username, password):
                st.session_state.authenticated = True
                st.session_state.promoter_name = username.upper()
                st.success(f"✅ Welcome, {username.upper()}!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
    
    # Show contact info instead of password hint
    st.markdown("---")
    st.caption("**Need access?** Contact your administrator to get your credentials.")


def logout():
    """Clear session and logout"""
    st.session_state.authenticated = False
    st.session_state.promoter_name = None
    st.session_state.submission_complete = False
    st.session_state.submission_result = None
    st.rerun()

# Check authentication
if not st.session_state.authenticated:
    # Custom CSS for login page
    st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Center content */
    .main > div {
        padding-top: 2rem;
        max-width: 700px;
        margin: 0 auto;
    }
    
    /* Header styling */
    .promoter-header {
        text-align: center;
        padding: 2rem 0;
    }
    
    .promoter-tag {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 8px 20px;
        border-radius: 25px;
        font-weight: 600;
        font-size: 14px;
        margin-bottom: 1rem;
    }
    
    .form-title {
        color: #2d3748;
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .form-subtitle {
        color: #718096;
        font-size: 16px;
        margin-bottom: 2rem;
    }
    
    /* Success/Error boxes */
    .success-box {
        background: #c6f6d5;
        border-left: 4px solid #48bb78;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
    }
    
    .error-box {
        background: #fed7d7;
        border-left: 4px solid #f56565;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
    }
    
    /* Form styling */
    .stTextInput > label, .stTextArea > label {
        font-weight: 600;
        color: #2d3748;
    }
    
    /* Button styling */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        padding: 0.75rem 2rem;
        border-radius: 8px;
        border: none;
        font-size: 16px;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
    }
</style>
""", unsafe_allow_html=True)
    
    # Show login page
    show_login_page()
    st.stop()

# User is authenticated - show the form
PROMOTER_SLUG = st.session_state.promoter_name

# Add logout button in sidebar
with st.sidebar:
    st.write(f"**Logged in as:** {PROMOTER_SLUG}")
    if st.button("🚪 Logout"):
        logout()

# Header
st.markdown(f"""
<div class="promoter-header">
    <div class="promoter-tag">{PROMOTER_SLUG}</div>
    <div class="form-title">BNG Quote Request</div>
    <div class="form-subtitle">Fast, simple biodiversity net gain quotes</div>
</div>
""", unsafe_allow_html=True)

# Show success or error if submission was made
if st.session_state.submission_complete and st.session_state.submission_result:
    result = st.session_state.submission_result
    
    if result['success']:
        if result['auto_quoted']:
            st.markdown('<div class="success-box">', unsafe_allow_html=True)
            st.success("✅ Quote Generated Successfully!")
            st.write(f"**Quote Total:** £{result['quote_total']:,.2f}")
            st.write(f"**Submission ID:** #{result['submission_id']}")
            
            if result.get('pdf_content'):
                st.download_button(
                    label="📄 Download Quote PDF",
                    data=result['pdf_content'],
                    file_name=f"BNG_Quote_{PROMOTER_SLUG}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="success-box">', unsafe_allow_html=True)
            st.success("✅ Quote Request Received!")
            st.write(f"**Quote Total:** £{result['quote_total']:,.2f}")
            st.write(f"**Submission ID:** #{result['submission_id']}")
            st.info("""
            Because this quote exceeds £20,000, it requires manual review.
            Our team will contact you shortly with a detailed proposal.
            """)
            st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Submit Another Quote"):
            st.session_state.submission_complete = False
            st.session_state.submission_result = None
            st.rerun()
    else:
        st.markdown('<div class="error-box">', unsafe_allow_html=True)
        st.error(f"❌ Error: {result.get('error', 'Unknown error occurred')}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Try Again"):
            st.session_state.submission_complete = False
            st.session_state.submission_result = None
            st.rerun()
    
    st.stop()

# Form
with st.form("promoter_form"):
    st.subheader("Contact Information")
    contact_email = st.text_input(
        "Contact Email *",
        placeholder="your.email@example.com",
        help="We'll send the quote and any follow-up information to this email"
    )
    
    st.subheader("Site Location")
    col1, col2 = st.columns(2)
    with col1:
        site_address = st.text_input(
            "Site Address",
            placeholder="123 Main Street, Town",
            help="Full site address (optional if postcode provided)"
        )
    with col2:
        site_postcode = st.text_input(
            "Postcode",
            placeholder="SW1A 1AA",
            help="Site postcode (optional if address provided)"
        )
    
    st.caption("⚠️ Please provide at least one of address or postcode")
    
    st.subheader("Additional Details")
    client_reference = st.text_input(
        "Client Reference (optional)",
        placeholder="Project reference or identifier"
    )
    
    notes = st.text_area(
        "Notes (optional)",
        placeholder="Any additional information or special requirements",
        height=100
    )
    
    st.subheader("BNG Metric File")
    metric_file = st.file_uploader(
        "Upload Metric File *",
        type=['xlsx'],
        help=f"Excel file (.xlsx) only, maximum {MAX_FILE_SIZE_MB} MB"
    )
    
    st.subheader("Consent")
    consent = st.checkbox(
        "I confirm that I have permission to share this data for the purpose of obtaining a BNG quote *",
        value=False
    )
    
    st.markdown("---")
    submitted = st.form_submit_button("🚀 Submit Quote Request", use_container_width=True)

# Process form submission
if submitted:
    # Validation
    errors = []
    
    if not contact_email:
        errors.append("Contact email is required")
    elif '@' not in contact_email:
        errors.append("Please enter a valid email address")
    
    if not site_address and not site_postcode:
        errors.append("Please provide either a site address or postcode")
    
    if not metric_file:
        errors.append("Please upload a BNG metric file")
    elif metric_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        errors.append(f"File size exceeds {MAX_FILE_SIZE_MB} MB limit")
    
    if not consent:
        errors.append("You must provide consent to share data")
    
    if errors:
        st.error("Please fix the following errors:")
        for error in errors:
            st.write(f"• {error}")
    else:
        # Process submission
        with st.spinner("Processing your quote request..."):
            try:
                # Save the file content for email attachment
                metric_file_content = metric_file.getvalue()
                metric_file_name = metric_file.name
                
                # Read metric file directly from uploaded file
                try:
                    demand_data = metric_reader.parse_metric_requirements(metric_file)
                except Exception as e:
                    st.session_state.submission_result = {
                        'success': False,
                        'error': f"Failed to read metric file: {str(e)}"
                    }
                    st.session_state.submission_complete = True
                    st.rerun()
                
                # Extract demand habitats from parsed data
                # parse_metric_requirements returns DataFrames for area, hedgerows, watercourses
                area_df = demand_data.get('area', pd.DataFrame())
                hedgerow_df = demand_data.get('hedgerows', pd.DataFrame())
                watercourse_df = demand_data.get('watercourses', pd.DataFrame())
                
                # Convert DataFrames to list of dicts for storage
                demand_habitats = area_df.to_dict('records') if not area_df.empty else []
                hedgerow_habitats = hedgerow_df.to_dict('records') if not hedgerow_df.empty else []
                watercourse_habitats = watercourse_df.to_dict('records') if not watercourse_df.empty else []
                
                # GEOCODE THE POSTCODE TO GET LPA/NCA
                target_lpa = ""
                target_nca = ""
                lpa_neighbors = []
                nca_neighbors = []
                lpa_neighbors_norm = []
                nca_neighbors_norm = []
                
                try:
                    if site_postcode:
                        st.write(f"🔄 **Geocoding postcode:** {site_postcode}")
                        
                        # Import geocoding functions from app.py
                        from app import get_postcode_info, get_lpa_nca_for_point, get_catchment_geo_for_point, layer_intersect_names, LPA_URL, NCA_URL
                        
                        # Get coordinates from postcode
                        lat, lon, _ = get_postcode_info(site_postcode)
                        st.write(f"📍 Location: {lat:.4f}, {lon:.4f}")
                        
                        # Get LPA and NCA
                        target_lpa, target_nca = get_lpa_nca_for_point(lat, lon)
                        st.write(f"🏛️ LPA: {target_lpa}")
                        st.write(f"🌳 NCA: {target_nca}")
                        
                        # Get geometries and neighbors for proper tier allocation
                        lpa_name, lpa_gj, nca_name, nca_gj = get_catchment_geo_for_point(lat, lon)
                        
                        if lpa_gj:
                            lpa_neighbors = layer_intersect_names(LPA_URL, lpa_gj, "LAD24NM")
                            lpa_neighbors = [n for n in lpa_neighbors if n != target_lpa]
                            lpa_neighbors_norm = [n.lower().replace(" ", "") for n in lpa_neighbors]
                            st.write(f"🔗 Adjacent LPAs: {len(lpa_neighbors)}")
                        
                        if nca_gj:
                            nca_neighbors = layer_intersect_names(NCA_URL, nca_gj, "NCA_Name")
                            nca_neighbors = [n for n in nca_neighbors if n != target_nca]
                            nca_neighbors_norm = [n.lower().replace(" ", "") for n in nca_neighbors]
                            st.write(f"🔗 Adjacent NCAs: {len(nca_neighbors)}")
                            
                    elif site_address:
                        st.write(f"ℹ️ Address provided but no postcode - using far tier for all banks")
                    else:
                        st.write(f"ℹ️ No location provided - using far tier for all banks")
                        
                except Exception as geo_error:
                    st.write(f"⚠️ Geocoding warning: {str(geo_error)[:100]}")
                    st.write("ℹ️ Continuing with empty location (far tier)")
                
                # RUN THE FULL OPTIMIZER using the optimise function from app.py
                allocation_df = pd.DataFrame()
                quote_total = 0.0
                
                st.write("🔄 **Processing metric file...**")
                st.write(f"- Area habitats: {len(demand_habitats)}")
                st.write(f"- Hedgerow habitats: {len(hedgerow_habitats)}")
                st.write(f"- Watercourse habitats: {len(watercourse_habitats)}")
                
                try:
                    if not demand_df.empty:
                        st.write("🔄 **Running full optimizer...**")
                        
                        # Import the optimise function from app.py
                        if HAS_CLIENT_REPORT_FUNCTION:  # If app.py imports worked
                            from app import optimise
                            
                            # Run optimization with actual location data
                            allocation_df, quote_total, status_msg = optimise(
                                demand_df=demand_df,
                                target_lpa=target_lpa,
                                target_nca=target_nca,
                                lpa_neigh=lpa_neighbors,
                                nca_neigh=nca_neighbors,
                                lpa_neigh_norm=lpa_neighbors_norm,
                                nca_neigh_norm=nca_neighbors_norm
                            )
                            
                            st.write(f"✅ **Optimizer complete:** {len(allocation_df)} allocations, £{quote_total:,.2f} total")
                            st.write(f"ℹ️ {status_msg}")
                        else:
                            raise Exception("app.py not available for optimization")
                    else:
                        raise Exception("No demand data to optimize")
                        
                except Exception as opt_error:
                    st.write(f"⚠️ Optimizer failed: {str(opt_error)[:200]}")
                    st.write("ℹ️ Using fallback simplified pricing...")
                    # Fallback: Calculate simplified quote total
                    total_units = 0.0
                    for h in demand_habitats:
                        total_units += float(h.get('units', 0) or 0)
                    for h in hedgerow_habitats:
                        total_units += float(h.get('units', 0) or 0)
                    for h in watercourse_habitats:
                        total_units += float(h.get('units', 0) or 0)
                    
                    quote_total = total_units * 10000.0  # £10k per unit estimate
                    st.write(f"📊 Total units: {total_units:.2f}")
                    st.write(f"💰 Estimated cost: £{quote_total:,.2f} (simplified pricing)")
                
                # Apply threshold logic
                auto_quoted = quote_total < AUTO_QUOTE_THRESHOLD
                
                # Save to database
                db = SubmissionsDB()
                
                # Demand dataframe is already available from parsing
                demand_df = area_df if not area_df.empty else pd.DataFrame()
                # allocation_df is already set from optimizer run above
                
                # Prepare manual rows (for hedgerow and watercourse)
                manual_hedgerow_rows = hedgerow_habitats
                manual_watercourse_rows = watercourse_habitats
                
                # Save submission using correct method
                submission_id = db.store_submission(
                    client_name=contact_email.split('@')[0],  # Use email prefix as name
                    reference_number=client_reference if client_reference else f"PROM-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                    site_location=site_address if site_address else site_postcode,
                    target_lpa=target_lpa,  # From postcode geocoding
                    target_nca=target_nca,
                    target_lat=None,
                    target_lon=None,
                    lpa_neighbors=lpa_neighbors,
                    nca_neighbors=nca_neighbors,
                    demand_df=demand_df,
                    allocation_df=allocation_df,
                    contract_size='Standard',
                    total_cost=quote_total,
                    admin_fee=0.0,
                    manual_hedgerow_rows=manual_hedgerow_rows,
                    manual_watercourse_rows=manual_watercourse_rows,
                    manual_area_habitat_rows=demand_habitats,
                    username='promoter',
                    promoter_name=PROMOTER_SLUG,
                    promoter_discount_type=None,
                    promoter_discount_value=None
                )
                
                # Generate PDF if auto-quoted
                pdf_content = None
                if auto_quoted:
                    try:
                        st.write("📄 **Generating PDF quote...**")
                        st.write(f"- Allocation data: {len(allocation_df)} rows" if not allocation_df.empty else "- No allocation data")
                        st.write(f"- PDF library available: {PDF_GENERATION_AVAILABLE}")
                        st.write(f"- Client report function available: {HAS_CLIENT_REPORT_FUNCTION}")
                        
                        # Generate client report table if we have allocation data
                        report_df = None
                        email_html = None
                        
                        if HAS_CLIENT_REPORT_FUNCTION and not allocation_df.empty:
                            st.write("🔄 Generating full client report with allocations...")
                            report_df, email_html = generate_client_report_table_fixed(
                                alloc_df=allocation_df,
                                demand_df=demand_df,
                                total_cost=quote_total,
                                admin_fee=0.0,
                                client_name=contact_email.split('@')[0],
                                ref_number=client_reference if client_reference else f"PROM-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                                location=site_address if site_address else site_postcode,
                                manual_hedgerow_rows=manual_hedgerow_rows,
                                manual_watercourse_rows=manual_watercourse_rows,
                                manual_area_rows=demand_habitats,
                                removed_allocation_rows=[],
                                promoter_name=PROMOTER_SLUG,
                                promoter_discount_type=None,
                                promoter_discount_value=None,
                                suo_discount_fraction=0.0
                            )
                            st.write(f"✅ Report table: {len(report_df)} rows" if report_df is not None else "⚠️ Report table empty")
                        
                        # If we don't have allocation data, create a simple summary
                        if report_df is None or report_df.empty:
                            st.write("ℹ️ Creating simplified summary (no allocations available)...")
                            summary_data = []
                            for idx, hab in enumerate(demand_habitats, 1):
                                summary_data.append({
                                    'Item': f"Area Habitat {idx}",
                                    'Habitat': hab.get('habitat_name', 'Unknown'),
                                    'Units': f"{hab.get('units', 0):.2f}",
                                    'Est. Cost': f"£{float(hab.get('units', 0) or 0) * 10000:,.0f}"
                                })
                            for idx, hab in enumerate(hedgerow_habitats, 1):
                                summary_data.append({
                                    'Item': f"Hedgerow {idx}",
                                    'Habitat': hab.get('habitat_name', 'Hedgerow'),
                                    'Units': f"{hab.get('units', 0):.2f}",
                                    'Est. Cost': f"£{float(hab.get('units', 0) or 0) * 10000:,.0f}"
                                })
                            for idx, hab in enumerate(watercourse_habitats, 1):
                                summary_data.append({
                                    'Item': f"Watercourse {idx}",
                                    'Habitat': hab.get('habitat_name', 'Watercourse'),
                                    'Units': f"{hab.get('units', 0):.2f}",
                                    'Est. Cost': f"£{float(hab.get('units', 0) or 0) * 10000:,.0f}"
                                })
                            report_df = pd.DataFrame(summary_data) if summary_data else None
                        
                        # Generate PDF
                        if PDF_GENERATION_AVAILABLE and report_df is not None and not report_df.empty:
                            st.write("🔄 Creating PDF with ReportLab...")
                            pdf_content = generate_quote_pdf(
                                client_name=contact_email.split('@')[0],
                                reference_number=client_reference if client_reference else f"PROM-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                                site_location=site_address if site_address else site_postcode,
                                quote_total=quote_total,
                                admin_fee=0.0,
                                report_df=report_df,
                                email_html=email_html or "",
                                promoter_name=PROMOTER_SLUG,
                                contact_email=contact_email,
                                notes=notes
                            )
                            st.write(f"✅ **PDF generated: {len(pdf_content):,} bytes**")
                        else:
                            raise Exception("Cannot generate PDF - missing data or library")
                            
                    except Exception as pdf_error:
                        st.write(f"⚠️ PDF generation issue: {str(pdf_error)[:200]}")
                        st.write("ℹ️ Creating text-based quote...")
                        # Create a simple text fallback
                        total_units = sum(float(h.get('units', 0) or 0) for h in demand_habitats)
                        total_units += sum(float(h.get('units', 0) or 0) for h in hedgerow_habitats)
                        total_units += sum(float(h.get('units', 0) or 0) for h in watercourse_habitats)
                        
                        pdf_content = f"""BNG QUOTE SUMMARY

Promoter: {PROMOTER_SLUG}
Reference: {client_reference if client_reference else f"PROM-{datetime.now().strftime('%Y%m%d-%H%M%S')}"}
Contact: {contact_email}
Site: {site_address if site_address else site_postcode}

HABITAT REQUIREMENTS:
{len(demand_habitats)} area habitats
{len(hedgerow_habitats)} hedgerow habitats  
{len(watercourse_habitats)} watercourse habitats

Total Units: {total_units:.2f}
{"Allocation: " + str(len(allocation_df)) + " bank allocations" if not allocation_df.empty else "Pricing: Simplified estimate"}
Total Cost: £{quote_total:,.2f}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{"Note: Full PDF generation encountered an error. This is a simplified text quote." if not allocation_df.empty else "Note: This is a preliminary estimate. Full optimizer requires location data for precise bank allocation."}

For detailed quotes and bank allocation details, please contact:
quotes@wildcapital.co.uk
""".encode('utf-8')
                        st.write(f"✅ Text quote created: {len(pdf_content)} bytes")
                
                # Always send email notification for record keeping
                email_sent = False
                try:
                    email_sent = send_manual_review_email(
                        promoter_name=PROMOTER_SLUG,
                        contact_email=contact_email,
                        site_location=site_address if site_address else site_postcode,
                        client_reference=client_reference,
                        notes=notes,
                        quote_total=quote_total,
                        submission_id=submission_id,
                        metric_file_content=metric_file_content,
                        metric_file_name=metric_file_name
                    )
                except Exception as email_error:
                    print(f"Email sending failed: {str(email_error)}")
                    email_sent = False
                
                # Store result (including file content for email)
                st.session_state.submission_result = {
                    'success': True,
                    'auto_quoted': auto_quoted,
                    'quote_total': quote_total,
                    'submission_id': submission_id,
                    'pdf_content': pdf_content,
                    'email_sent': email_sent,
                    'metric_file_content': metric_file_content,
                    'metric_file_name': metric_file_name,
                    'contact_email': contact_email,
                    'site_location': site_address if site_address else site_postcode,
                    'client_reference': client_reference,
                    'notes': notes
                }
                st.session_state.submission_complete = True
                st.rerun()
                
            except Exception as e:
                st.session_state.submission_result = {
                    'success': False,
                    'error': str(e)
                }
                st.session_state.submission_complete = True
                st.rerun()

# Footer
st.markdown("---")
st.caption(f"Promoter: {PROMOTER_SLUG} | Powered by Wild Capital BNG Optimiser")
