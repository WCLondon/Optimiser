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
from app import generate_client_report_table_fixed

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
                
                # Calculate simplified quote total
                # In production, this would run the full optimizer
                total_units = sum(h.get('units', 0) for h in demand_habitats)
                total_units += sum(h.get('units', 0) for h in hedgerow_habitats)
                total_units += sum(h.get('units', 0) for h in watercourse_habitats)
                
                # Simplified pricing (£10,000 per unit average)
                quote_total = total_units * 10000.0
                
                # Apply threshold logic
                auto_quoted = quote_total < AUTO_QUOTE_THRESHOLD
                
                # Save to database
                db = SubmissionsDB()
                
                # Convert demand data to DataFrames for storage
                demand_df = area_df if not area_df.empty else pd.DataFrame()
                allocation_df = pd.DataFrame()  # No allocation yet, placeholder
                
                # Prepare manual rows (for hedgerow and watercourse)
                manual_hedgerow_rows = hedgerow_habitats
                manual_watercourse_rows = watercourse_habitats
                
                # Save submission using correct method
                submission_id = db.store_submission(
                    client_name=contact_email.split('@')[0],  # Use email prefix as name
                    reference_number=client_reference if client_reference else f"PROM-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                    site_location=site_address if site_address else site_postcode,
                    target_lpa='',  # Would be resolved from postcode
                    target_nca='',
                    target_lat=None,
                    target_lon=None,
                    lpa_neighbors=[],
                    nca_neighbors=[],
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
                        # Generate client report table using the function from app.py
                        report_df, email_html = generate_client_report_table_fixed(
                            alloc_df=allocation_df,
                            demand_df=demand_df,
                            total_cost=quote_total,
                            admin_fee=0.0,  # No admin fee for promoter quotes
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
                        
                        # Generate PDF using the report
                        if PDF_GENERATION_AVAILABLE:
                            pdf_content = generate_quote_pdf(
                                client_name=contact_email.split('@')[0],
                                reference_number=client_reference if client_reference else f"PROM-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                                site_location=site_address if site_address else site_postcode,
                                quote_total=quote_total,
                                admin_fee=0.0,
                                report_df=report_df,
                                email_html=email_html,
                                promoter_name=PROMOTER_SLUG,
                                contact_email=contact_email,
                                notes=notes
                            )
                        else:
                            # Fallback: create a simple text file as PDF
                            pdf_content = f"""
BNG QUOTE SUMMARY

Promoter: {PROMOTER_SLUG}
Reference: {client_reference if client_reference else f"PROM-{datetime.now().strftime('%Y%m%d-%H%M%S')}"}
Contact: {contact_email}
Site: {site_address if site_address else site_postcode}

Total Cost: £{quote_total:,.2f}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Note: Install reportlab for full PDF generation with client report table.
""".encode('utf-8')
                    except Exception as pdf_error:
                        print(f"PDF generation failed: {str(pdf_error)}")
                        # Create a simple text fallback
                        pdf_content = f"BNG Quote - {PROMOTER_SLUG}\nTotal: £{quote_total:,.2f}\nSite: {site_address if site_address else site_postcode}".encode('utf-8')
                
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
